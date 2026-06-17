from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
import gzip

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS
import duckdb
import chardet

from utils.log_util import get_logger
from package.rdf_build_support import (
    open_text_writer,
)

logger = get_logger()


GENCC_SOURCE_URI = "https://search.thegencc.org/download/action/submissions-export-csv"

GENCC = Namespace("https://search.thegencc.org/submissions/")
GENE_CONTEXT = Namespace("https://pubcasefinder.dbcls.jp/gene_context/")
MIM = Namespace("https://omim.org/entry/")
NANDO = Namespace("http://nanbyodata.jp/ontology/nando#")
NANDO_DISEASE = Namespace("http://nanbyodata.jp/ontology/NANDO_")
NCBIGENE = Namespace("http://identifiers.org/ncbigene/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
ORDO = Namespace("http://www.orpha.net/ORDO/")
SIO = Namespace("http://semanticscience.org/resource/")


AssociationMap = dict[str, list[str]]


@dataclass
class MondoMapping:
    mondo_to_omim: dict[str, list[str]] = field(default_factory=dict)
    mondo_to_orpha: dict[str, list[str]] = field(default_factory=dict)
    omim_to_mondo: dict[str, list[str]] = field(default_factory=dict)
    orpha_to_mondo: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class MergeStats:
    added: int = 0
    overlap: int = 0


@dataclass
class GenCCAssociations:
    omim_associations: AssociationMap = field(default_factory=dict)
    orphanet_associations: AssociationMap = field(default_factory=dict)
    mondo_associations: AssociationMap = field(default_factory=dict)


@dataclass
class GenCCSubmissionRecord:
    association_uri: URIRef
    disease_uri: URIRef
    gene_uri: URIRef
    submission_uri: URIRef
    classification_title: str
    inheritance_uri: URIRef | None
    submitter_label: str


GENCC_SUBMITTER_LABELS = {
    "GENCC:000101": "Ambry Genetics",
    "GENCC:000102": "ClinGen",
    "GENCC:000103": "DECIPHER",
    "GENCC:000104": "Genomics England PanelApp",
    "GENCC:000105": "Illumina",
    "GENCC:000106": "Invitae",
    "GENCC:000107": "Laboratory for Molecular Medicine",
    "GENCC:000108": "Myriad Women's Health",
    "GENCC:000109": "Online Mendelian Inheritance in Man (OMIM)",
    "GENCC:000110": "Orphanet",
    "GENCC:000111": "PanelApp Australia",
    "GENCC:000112": "TGMI G2P",
    "GENCC:000113": "Franklin by Genoox",
    "GENCC:000114": "King Faisal Specialist Hospital and Research Center",
}


def load_ncbi_gene_symbol_map(path: str | Path) -> dict[str, str]:
    logger.info("loading NCBI gene symbol map: path=%s", path)
    ncbi_gene_symbol_map: dict[str, str] = {}
    con = duckdb.connect()
    query_statement = f"""
        select
            cast(GeneID as varchar),
            Symbol
        from read_csv('{path}', delim='\\t')
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()
        if row is None:
            break
        if row[1] not in ncbi_gene_symbol_map:
            ncbi_gene_symbol_map[row[1]] = row[0]
    logger.info("loaded NCBI gene symbol map: path=%s symbols=%s", path, len(ncbi_gene_symbol_map))
    return ncbi_gene_symbol_map

# ncbiのHomo_sapience.gene_infoからhgncid: dxrefをマッピング
def load_hgnc_to_ncbi_map(path: str | Path) -> dict[str, str]:
    logger.info("loading HGNC to NCBI map: path=%s", path)
    hgnc_to_ncbi_map: dict[str, str] = {}
    con = duckdb.connect()
    query_statement = f"select cast(GeneID as varchar), dbXrefs from read_csv('{path}', delim='\\t')"
    res = con.execute(query_statement)

    while True:
        row = res.fetchone()

        if row is None:
            break

        hgnc_id = extract_hgnc_id(row[1])
        if hgnc_id is not None and hgnc_id not in hgnc_to_ncbi_map:
            hgnc_to_ncbi_map[hgnc_id] = row[0]

    logger.info("loaded HGNC to NCBI map: path=%s mappings=%s", path, len(hgnc_to_ncbi_map))
    return hgnc_to_ncbi_map

# gencc-submissions.tsvとhgncidのdxrefを紐づけ
def load_gencc_submission_records(
    gencc_submissions_path: str,
    ncbi_gene_info_path: str,
) -> list[GenCCSubmissionRecord]:
    logger.info(
        "loading GenCC submission records: submissions=%s ncbi_gene_info=%s",
        gencc_submissions_path,
        ncbi_gene_info_path,
    )
    hgnc_to_ncbi_map = load_hgnc_to_ncbi_map(ncbi_gene_info_path)
    records: list[GenCCSubmissionRecord] = []

    con = duckdb.connect()
    query_statement = f"""
        select
            uuid,
            gene_curie,
            disease_original_curie,
            submitted_as_submitter_id,
            classification_title,
            moi_curie
        from
            read_csv('{gencc_submissions_path}', delim='\\t')
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()

        if row is None:
            break

        gencc_id = row[0].replace(" ", "")
        hgnc_id  = row[1].strip().removeprefix('HGNC:')
        disease_curie = row[2].strip()
        disease_reference = to_gencc_disease_reference(disease_curie)

        if gencc_id is None or not hgnc_id or disease_reference is None:
            continue

        ncbi_gene_id = hgnc_to_ncbi_map.get(hgnc_id)
        if ncbi_gene_id is None:
            continue
        moi_curie = row[5]
        if moi_curie is None:
            moi_curie = ''

        disease_path, disease_uri = disease_reference
        submitter_id = row[3]

        records.append(
            GenCCSubmissionRecord(
                association_uri=GENE_CONTEXT[f"disease:{disease_path}/gene:ENT:{ncbi_gene_id}"],
                disease_uri=disease_uri,
                gene_uri=NCBIGENE[ncbi_gene_id],
                submission_uri=GENCC[gencc_id],
                classification_title=row[4].strip() or "",
                inheritance_uri=to_hpo_uri(moi_curie) ,
                submitter_label=resolve_gencc_submitter_label(submitter_id),
            )
        )
    logger.info("loaded GenCC submission records: submissions=%s records=%s", gencc_submissions_path, len(records))
    return records

def load_orphanet_gene_associations(
    ncbi_gene_path: str | Path,
    orphanet_xml_path: str | Path,
) -> AssociationMap:
    logger.info(
        "loading Orphanet gene associations: ncbi_gene=%s orphanet_xml=%s",
        ncbi_gene_path,
        orphanet_xml_path,
    )
    ncbi_gene_symbol_map = load_ncbi_gene_symbol_map(ncbi_gene_path)
    associations: AssociationMap = {}

    tree = ET.parse(orphanet_xml_path)
    root = tree.getroot()
    for disorder_list in root.iter("DisorderList"):
        for disorder in disorder_list.iter("Disorder"):
            orpha_number = disorder.find(".//OrphaCode")
            if orpha_number is None or orpha_number.text is None:
                continue

            for symbol in disorder.findall(".//Symbol"):
                if symbol.text is None:
                    continue
                ncbi_id = ncbi_gene_symbol_map.get(symbol.text)
                if ncbi_id is not None:
                    add_association(associations, orpha_number.text, ncbi_id, "Orphanet")

    logger.info("loaded Orphanet gene associations: orphanet_xml=%s associations=%s", orphanet_xml_path, len(associations))
    return associations

def load_omim_gene_associations(path: str | Path) -> AssociationMap:
    logger.info("loading OMIM gene associations: path=%s", path)
    associations: AssociationMap = {}
    con = duckdb.connect()
    query_statement = f"""
        select
            cast("#MIM number" as varchar),
            cast(GeneID as varchar)
        from
            read_csv('{path}', delim='\\t')
        where
            type = 'phenotype' and GeneID != '-'
    """
    res = con.execute(query_statement)

    while True:
        row = res.fetchone()
        if row is None:
            break
        add_association(associations, row[0], row[1], "MedGen")

    logger.info("loaded OMIM gene associations: path=%s associations=%s", path, len(associations))
    return associations

def load_gencc_definitive_associations(
    ncbigene_gene_info_path: str,
    mondo_owl_path: str,
    gencc_submissions_path: str,
) -> GenCCAssociations:
    logger.info("loading definitive GenCC associations")
    # 遺伝子と疾患の関係性が確実なもののみを取り扱う
    return load_gencc_associations(
        ncbigene_gene_info_path,
        mondo_owl_path,
        gencc_submissions_path,
        {"GENCC:100001"}, project_mondo_to_mapped_diseases=True
    )

# gencc-submissions.tsvとmondo-international.owlからncbiの遺伝子IDとmondo, omim, orphanetのidを紐づける
def load_gencc_associations(
    ncbigene_gene_info_path: str,
    mondo_owl_path: str,
    gencc_submissions_path: str,
    allowed_classification_curies: set[str] | None,
    *,
    project_mondo_to_mapped_diseases: bool,
) -> GenCCAssociations:
    logger.info(
        "loading GenCC associations: ncbi_gene_info=%s mondo_owl=%s submissions=%s project_mondo=%s",
        ncbigene_gene_info_path,
        mondo_owl_path,
        gencc_submissions_path,
        project_mondo_to_mapped_diseases,
    )
    hgnc_to_ncbi_map = load_hgnc_to_ncbi_map(ncbigene_gene_info_path)
    mondo_mapping = load_mondo_mapping_from_owl(mondo_owl_path)
    associations = GenCCAssociations()

    con = duckdb.connect()
    query_statement = f"""
        select
            gene_curie,
            disease_curie,
            disease_original_curie,
            classification_curie,
        from
            read_csv('{gencc_submissions_path}', delim='\\t')
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()

        if row is None:
            break

        hgnc_id = normalize_curie_value(row[0], "HGNC:")
        disease_curie = normalize_value(row[1])
        original_disease_curie = normalize_value(row[2])
        classification_curie = normalize_value(row[3])

        if allowed_classification_curies is not None and classification_curie not in allowed_classification_curies:
            continue

        ncbi_id = hgnc_to_ncbi_map.get(hgnc_id)
        if ncbi_id is None:
            continue

        if original_disease_curie and ":" in original_disease_curie:
            add_original_disease_association(associations, ncbi_id, original_disease_curie)

        if disease_curie is not None and disease_curie.startswith("MONDO:"):
            mondo_id = normalize_curie_value(disease_curie, "MONDO:")
            add_association(associations.mondo_associations, mondo_id, ncbi_id, "GenCC")

            if project_mondo_to_mapped_diseases:
                project_gene_to_mapped_diseases(
                    associations.omim_associations,
                    mondo_mapping.mondo_to_omim,
                    mondo_id,
                    ncbi_id,
                    "GenCC",
                )
                project_gene_to_mapped_diseases(
                    associations.orphanet_associations,
                    mondo_mapping.mondo_to_orpha,
                    mondo_id,
                    ncbi_id,
                    "GenCC",
                )

    logger.info(
        "loaded GenCC associations: omim=%s orphanet=%s mondo=%s",
        len(associations.omim_associations),
        len(associations.orphanet_associations),
        len(associations.mondo_associations),
    )
    return associations

def add_original_disease_association(
    associations: GenCCAssociations,
    ncbi_id: str,
    original_disease_curie: str,
) -> None:
    if original_disease_curie.startswith("OMIM:"):
        add_association(
            associations.omim_associations,
            normalize_curie_value(original_disease_curie, "OMIM:"),
            ncbi_id,
            "GenCC",
        )
    elif original_disease_curie.startswith("Orphanet:"):
        add_association(
            associations.orphanet_associations,
            normalize_curie_value(original_disease_curie, "Orphanet:"),
            ncbi_id,
            "GenCC",
        )
    elif original_disease_curie.startswith("MONDO:"):
        add_association(
            associations.mondo_associations,
            normalize_curie_value(original_disease_curie, "MONDO:"),
            ncbi_id,
            "GenCC",
        )

def load_mondo_mapping_from_owl(mondo_owl_path: str | Path) -> MondoMapping:
    logger.info("loading MONDO mapping from OWL: path=%s", mondo_owl_path)
    mapping = MondoMapping()
    graph = Graph()
    graph.parse(str(mondo_owl_path), format="xml")

    # 主述が完全一致のものを取得
    for mondo_uri, _, exact_match_uri in graph.triples((None, SKOS.exactMatch, None)):
        mondo_id = extract_mondo_id_from_uri(str(mondo_uri))
        if mondo_id is None:
            continue
        if is_deprecated_resource(graph, mondo_uri):
            continue

        exact_match = str(exact_match_uri)
        omim_id = extract_omim_id(exact_match)
        if omim_id is not None:
            add_to_mapping(mapping.mondo_to_omim, mondo_id, omim_id)
            add_to_mapping(mapping.omim_to_mondo, omim_id, mondo_id)

        orpha_id = extract_orphanet_id(exact_match)
        if orpha_id is not None:
            add_to_mapping(mapping.mondo_to_orpha, mondo_id, orpha_id)
            add_to_mapping(mapping.orpha_to_mondo, orpha_id, mondo_id)

    logger.info(
        "loaded MONDO mapping from OWL: path=%s mondo_to_omim=%s mondo_to_orpha=%s omim_to_mondo=%s orpha_to_mondo=%s",
        mondo_owl_path,
        len(mapping.mondo_to_omim),
        len(mapping.mondo_to_orpha),
        len(mapping.omim_to_mondo),
        len(mapping.orpha_to_mondo),
    )
    return mapping

def project_gene_to_mapped_diseases(
    target_associations: AssociationMap,
    mondo_mapping: dict[str, list[str]],
    mondo_id: str,
    ncbi_id: str,
    source: str,
) -> None:
    mapped_ids = mondo_mapping.get(mondo_id)
    if mapped_ids is None:
        return

    for mapped_id in mapped_ids:
        add_association(target_associations, mapped_id, ncbi_id, source)

def merge_association_maps(target: AssociationMap, source: AssociationMap) -> None:
    before_count = len(target)
    added_count = 0
    overlap_count = 0
    for key, source_names in source.items():
        disease_id, gene_id = key.split("\t")
        for source_name in source_names:
            if add_association(target, disease_id, gene_id, source_name):
                added_count += 1
            else:
                overlap_count += 1
    logger.info(
        "merged association maps: source_associations=%s before=%s after=%s added=%s overlap=%s",
        len(source),
        before_count,
        len(target),
        added_count,
        overlap_count,
    )


def merge_associations_from_tsv(
    path: str | Path,
    associations: AssociationMap,
    disease_column: int,
    gene_column: int,
    source: str,
    ) -> MergeStats:
    logger.info(
        "merging associations from TSV: path=%s source=%s disease_column=%s gene_column=%s",
        path,
        source,
        disease_column,
        gene_column,
    )
    stats = MergeStats()
    original_path = path
    path = check_file_char_code(path)
    if not path:
        raise RuntimeError('file argument is empty')

    con = duckdb.connect()
    query_statement = f"""
        select
            {disease_column},
            {gene_column}
        from
            read_csv('{path}', delim='\\t')
        where
            {disease_column} is not null
            and {gene_column} is not null
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()
        if row is None:
            break
        if add_association(associations, str(row[0]), str(row[1]), source):
            stats.added += 1
        else:
            stats.overlap += 1
    logger.info(
        "merged associations from TSV: path=%s normalized_path=%s source=%s added=%s overlap=%s total_associations=%s",
        original_path,
        path,
        source,
        stats.added,
        stats.overlap,
        len(associations),
    )
    return stats

# utf-8でファイルを開こうとする
# もし開けない場合はcp949でファイルを開き、そのファイルの横にutf-8エンコードしたファイルを吐き出させる
# それでも開けない場合はerrorを返して処理を中断
def check_file_char_code(path: str | Path) -> str | Path:
    logger.info("checking file character code: path=%s", path)
    char_code = ''
    if Path(path).suffix == '.gz':
        with gzip.open(path, 'rb') as f:
            char_code = chardet.detect(f.read(), include_encodings=['utf-8','cp949'])
        return create_utf8_file(path, char_code['encoding'])
    else:
        with open(path, 'rb') as f:
            char_code = chardet.detect(f.read(), include_encodings=['utf-8','cp949'])
        return create_utf8_file(path, char_code['encoding'])

def create_utf8_file(path: str | Path, char_code: str):
    logger.info("detected file character code: path=%s encoding=%s", path, char_code)
    match char_code:
        case 'utf-8':
            return Path(path)
        case 'CP949':
            base_path = Path(path)
            if Path(path).suffix == '.gz':
                input_path_without_gz = base_path.with_suffix('')
                utf8_file_path = input_path_without_gz.with_name(
                    f'{input_path_without_gz.stem}_utf8{input_path_without_gz.suffix}'
                )
                with gzip.open(path, 'rt', encoding='cp949') as reader:
                    with open(utf8_file_path, 'w', encoding='utf-8') as writer:
                        writer.write(reader.read())
            else:
                utf8_file_path = base_path.with_name(f'{base_path.stem}_utf8{base_path.suffix}')
                with open(path, 'r', encoding='cp949') as reader:
                    with open(utf8_file_path, 'w', encoding='utf-8') as writer:
                        writer.write(reader.read())

            logger.info("created UTF-8 encoded file: source=%s output=%s", path, utf8_file_path)
            return utf8_file_path
        case None:
            logger.error(f'check the file character code: {path}')
            return None

def add_projected_mondo_associations(
    mondo_associations: AssociationMap,
    source_associations: AssociationMap,
    mondo_mapping: dict[str, list[str]],
) -> None:
    before_count = len(mondo_associations)
    added_count = 0
    for key, sources in source_associations.items():
        disease_id, ncbi_id = key.split("\t")
        mondo_ids = mondo_mapping.get(disease_id)
        if mondo_ids is None:
            continue

        for mondo_id in mondo_ids:
            for source in sources:
                if add_association(mondo_associations, mondo_id, ncbi_id, source):
                    added_count += 1
    logger.info(
        "added projected MONDO associations: source_associations=%s mappings=%s before=%s after=%s added=%s",
        len(source_associations),
        len(mondo_mapping),
        before_count,
        len(mondo_associations),
        added_count,
    )

def build_mondo_gene_associations(
    ncbigene_gene_info_path: str,
    mondo_owl_path: str,
    gencc_submissions_path: str,
    medgen_mim2gene_path: str,
    orphanet_product6_path: str,
) -> AssociationMap:
    logger.info("building MONDO gene associations")
    gencc_associations = load_gencc_definitive_associations(
        ncbigene_gene_info_path,
        mondo_owl_path,
        gencc_submissions_path
    )
    mondo_mapping = load_mondo_mapping_from_owl(mondo_owl_path)
    omim_ncbi_gene_map = load_omim_gene_associations(medgen_mim2gene_path)
    orphanet_ncbi_gene_map = load_orphanet_gene_associations(ncbigene_gene_info_path, orphanet_product6_path)

    mondo_ncbi_gene_map: AssociationMap = {}
    add_projected_mondo_associations(
        mondo_ncbi_gene_map,
        omim_ncbi_gene_map,
        mondo_mapping.omim_to_mondo,
    )
    add_projected_mondo_associations(
        mondo_ncbi_gene_map,
        orphanet_ncbi_gene_map,
        mondo_mapping.orpha_to_mondo,
    )
    merge_association_maps(mondo_ncbi_gene_map, gencc_associations.mondo_associations)
    logger.info("built MONDO gene associations: associations=%s", len(mondo_ncbi_gene_map))
    return mondo_ncbi_gene_map

# 第一引数で受け取ったmapにdisease_id\tgene_id: [sources]を入れる関数
def add_association(
    associations: AssociationMap,
    disease_id: str,
    gene_id: str,
    source: str,
) -> bool:
    key = f"{disease_id}\t{gene_id}"
    sources = associations.setdefault(key, [])
    if source in sources:
        return False
    sources.append(source)
    return True

def write_gene_association_ttl(
    output_path: str | Path,
    associations: AssociationMap,
    *,
    disease_context_prefix: str,
    disease_namespace_prefix: str,
    disease_namespace: Namespace,
    disease_id_prefix: str,
    source_uri_map: dict[str, URIRef],
) -> None:
    logger.info(
        "writing gene association TTL: output=%s associations=%s disease_context=%s",
        output_path,
        len(associations),
        disease_context_prefix,
    )
    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("ncbigene", NCBIGENE)
    graph.bind(disease_namespace_prefix, disease_namespace)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("sio", SIO)

    for key, sources in associations.items():
        disease_id, ncbi_id = key.split("\t")
        association_uri = GENE_CONTEXT[
            f"disease:{disease_context_prefix}:{disease_id}/gene:ENT:{ncbi_id}"
        ]
        disease_uri = disease_namespace[f"{disease_id_prefix}{disease_id}"]
        gene_uri = NCBIGENE[ncbi_id]

        graph.add((association_uri, RDF.type, SIO["SIO_000983"]))
        graph.add((association_uri, SIO["SIO_000628"], disease_uri))
        graph.add((association_uri, SIO["SIO_000628"], gene_uri))

        # source_mapにない値がソースに入っている場合、https://pubcasefinder.dbcls.jp/gene_context/disease:obo:0001/gene:ENT:1 のようなのがソースとして入る
        for source in sources:
            source_uri = source_uri_map.get(source)
            if source_uri is not None:
                graph.add((association_uri, DCTERMS.source, source_uri))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format="turtle"))
    logger.info("finished writing gene association TTL: output=%s triples=%s", output_path, len(graph))

def write_gencc_gene_association_ttl(
    output_path: str | Path,
    records: list[GenCCSubmissionRecord],
) -> None:
    logger.info("writing GenCC gene association TTL: output=%s records=%s", output_path, len(records))
    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("gencc", GENCC)
    graph.bind("nando", NANDO)
    graph.bind("ncbigene", NCBIGENE)
    graph.bind("mim", MIM)
    graph.bind("obo", OBO)
    graph.bind("ordo", ORDO)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("sio", SIO)

    for record in records:
        graph.add((record.association_uri, RDF.type, SIO["SIO_000983"]))
        graph.add((record.association_uri, SIO["SIO_000628"], record.disease_uri))
        graph.add((record.association_uri, SIO["SIO_000628"], record.gene_uri))
        graph.add((record.association_uri, DCTERMS.source, record.submission_uri))
        graph.add((record.submission_uri, OBO["IAO_0000114"], Literal(record.classification_title)))
        if record.inheritance_uri is not None:
            graph.add((record.submission_uri, NANDO.hasInheritance, record.inheritance_uri))
        graph.add((record.submission_uri, DCTERMS.creator, Literal(record.submitter_label)))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format="turtle"))
    logger.info("finished writing GenCC gene association TTL: output=%s triples=%s", output_path, len(graph))


def extract_hgnc_id(db_xrefs: str | None) -> str | None:
    if not db_xrefs:
        return None

    for ref in db_xrefs.split("|"):
        if ref.startswith("HGNC:HGNC:"):
            return ref.removeprefix("HGNC:HGNC:")
        if ref.startswith("HGNC:"):
            value = ref.removeprefix("HGNC:")
            return value.removeprefix("HGNC:")
    return None


def normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized.startswith('"') and normalized.endswith('"') and len(normalized) >= 2:
        normalized = normalized[1:-1]
    return normalized


def normalize_curie_value(value: str | None, prefix: str) -> str:
    normalized = normalize_value(value)
    if normalized is None:
        return ""
    return normalized.removeprefix(prefix)


def resolve_gencc_submitter_label(submitter_id: str | None) -> str:
    if submitter_id is None:
        return ""
    return GENCC_SUBMITTER_LABELS.get(submitter_id, submitter_id)


def to_gencc_disease_reference(disease_curie: str | None) -> tuple[str, URIRef] | None:
    if not disease_curie:
        return None
    if disease_curie.startswith("Orphanet:"):
        orphanet_id = disease_curie.removeprefix('Orphanet:')
        return f"ORDO:{orphanet_id}", ORDO[f"Orphanet_{orphanet_id}"]
    if disease_curie.startswith("OMIM:"):
        omim_id = disease_curie.removeprefix('OMIM:')
        return disease_curie, MIM[omim_id]
    if disease_curie.startswith("MONDO:"):
        mondo_id = disease_curie.removeprefix('MONDO:')
        return disease_curie, OBO[f"MONDO_{mondo_id}"]
    return None


def to_hpo_uri(hpo_curie: str) -> URIRef | None:
    hpo_id = hpo_curie.removeprefix('HP:')
    return OBO[f"HP_{hpo_id}"] if hpo_id else None

def add_to_mapping(mapping: dict[str, list[str]], key: str, value: str) -> None:
    # もし既存のキーが存在していたら、上書きせずに要素を作成する.valuesにはkeyに対してdictionaryのvalueが入る.
    values = mapping.setdefault(key, [])
    if value not in values:
        values.append(value)

def extract_mondo_id_from_uri(uri: str) -> str | None:
    marker = "http://purl.obolibrary.org/obo/MONDO_"
    start = uri.find(marker)
    if start < 0:
        return None
    return re.search(r'http://purl.obolibrary.org/obo/MONDO_(\d+)', uri).group(1)

def is_deprecated_resource(graph: Graph, uri: URIRef) -> bool:
    for value in graph.objects(uri, OWL.deprecated):
        if str(value).strip().lower() == "true":
            return True
    return False


def extract_omim_id(uri: str) -> str | None:
    for marker in ("/omim/", "omim.org/entry/"):
        start = uri.find(marker)
        if start < 0:
            continue
        return re.search(rf'{marker}(\d+)', uri).group(1)
    return None


def extract_orphanet_id(uri: str) -> str | None:
    marker = "Orphanet_"
    start = uri.find(marker)
    if start < 0:
        return None
    return re.search(rf'{marker}(\d+)', uri).group(1)
