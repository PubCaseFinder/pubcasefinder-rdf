from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
import csv
import xml.etree.ElementTree as ET

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS
import duckdb

from package.rdf_build_support import (
    load_config,
    open_text_reader,
    open_text_writer,
    resolve_configured_file,
    resolve_configured_output_dir,
    resolve_resource_root,
)


GENCC_SOURCE_URI = "https://search.thegencc.org/download/action/submissions-export-csv"

GENCC = Namespace("https://search.thegencc.org/submissions/")
GENE_CONTEXT = Namespace("https://pubcasefinder.dbcls.jp/gene_context/")
MIM = Namespace("https://omim.org/entry/")
NANDO = Namespace("http://nanbyodata.jp/ontology/nando#")
NCBIGENE = Namespace("http://identifiers.org/ncbigene/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
ORDO = Namespace("http://www.orpha.net/ORDO/")
SIO = Namespace("http://semanticscience.org/resource/")

CONFIG = load_config('config.ini')

NCBI_GENE_INFO_PATH = resolve_configured_file(
    CONFIG,
    "ncbigene.file.path",
    resolve_resource_root(CONFIG, "ncbigene.dir"),
    "Homo_sapiens.gene_info.gz",
    alternate_file_names=("Homo_sapiens.gene_info",),
)
MEDGEN_MIM2GENE_PATH = resolve_configured_file(
    CONFIG,
    "medgen.mim2gene.path",
    resolve_resource_root(CONFIG, "medgen.dir"),
    "mim2gene_medgen.txt",
)
ORPHANET_PRODUCT6_PATH = resolve_configured_file(
    CONFIG,
    "orphanet.product6.path",
    resolve_resource_root(CONFIG, "orphanet.dir"),
    "en_product6.xml",
)
MONDO_OWL_PATH = resolve_configured_file(
    CONFIG,
    "mondo.owl.path",
    resolve_resource_root(CONFIG, "mondo.dir"),
    "mondo-international.owl",
    alternate_file_names=("mondo.owl", "mondo.obo"),
)
GENCC_SUBMISSIONS_PATH = resolve_configured_file(
    CONFIG,
    "gencc.submissions.path",
    resolve_resource_root(CONFIG, "gencc.dir"),
    "gencc-submissions.tsv",
    alternate_file_names=("gencc-submissions.csv",),
)
NANDO_ASSOCIATION_PATH = resolve_configured_file(
    CONFIG,
    "panelsearch.association.path",
    resolve_resource_root(CONFIG, "panelsearch.dir"),
    "nando_gene_association.txt",
    required=False,
)
NANDO_MANUAL_PATH = resolve_configured_file(
    CONFIG,
    "panelsearch.manual.path",
    resolve_resource_root(CONFIG, "panelsearch.dir"),
    "shitei_gene_all_250819.txt",
    required=False,
)
RDF_DIR = resolve_configured_output_dir(CONFIG)


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
    return ncbi_gene_symbol_map


# ncbiのHomo_sapience.gene_infoからhgncid: dxrefをマッピング
def load_hgnc_to_ncbi_map(path: str | Path) -> dict[str, str]:
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

    return hgnc_to_ncbi_map

# gencc-submissions.tsvとhgncidのdxrefを紐づけ
def load_gencc_submission_records(
    gencc_submissions_path: str,
    ncbi_gene_info_path: str,
) -> list[GenCCSubmissionRecord]:
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

        gencc_id = row[0].strip()
        hgnc_id  = row[1].strip().removeprefix('HGNC:')
        disease_curie = row[2].strip()
        disease_reference = to_gencc_disease_reference(disease_curie)

        if gencc_id is None or not hgnc_id or disease_reference is None:
            continue

        ncbi_gene_id = hgnc_to_ncbi_map.get(hgnc_id)
        if ncbi_gene_id is None:
            continue

        disease_path, disease_uri = disease_reference
        submitter_id = row[3]

        records.append(
            GenCCSubmissionRecord(
                association_uri=GENE_CONTEXT[f"disease:{disease_path}/gene:ENT:{ncbi_gene_id}"],
                disease_uri=disease_uri,
                gene_uri=NCBIGENE[ncbi_gene_id],
                submission_uri=GENCC[gencc_id],
                classification_title=row[4].strip() or "",
                inheritance_uri=to_hpo_uri(row[5]) ,
                submitter_label=resolve_gencc_submitter_label(submitter_id),
            )
        )
    return records

def load_orphanet_gene_associations(
    ncbi_gene_path: str | Path,
    orphanet_xml_path: str | Path,
) -> AssociationMap:
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

    return associations


def load_omim_gene_associations(path: str | Path) -> AssociationMap:
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

    return associations


def load_gencc_definitive_associations(
    ncbigene_gene_info_path: str,
    mondo_owl_path: str,
    gencc_submissions_path: str,
) -> GenCCAssociations:
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
    for key, source_names in source.items():
        disease_id, gene_id = key.split("\t")
        for source_name in source_names:
            add_association(target, disease_id, gene_id, source_name)


def merge_associations_from_tsv(
    path: str | Path,
    associations: AssociationMap,
    disease_index: int,
    gene_index: int,
    source: str,
    *,
    skip_first_line: bool = False,
) -> MergeStats:
    stats = MergeStats()
    for line_number, line in enumerate(read_tsv_lines(path), start=1):
        if skip_first_line and line_number == 1:
            continue

        split = line.rstrip("\n").split("\t")
        if len(split) > max(disease_index, gene_index):
            if add_association(associations, split[disease_index], split[gene_index], source):
                stats.added += 1
            else:
                stats.overlap += 1

    return stats


def read_tsv_lines(path: str | Path) -> list[str]:
    try:
        with open_text_reader(path) as reader:
            return list(reader)
    except UnicodeDecodeError:
        try:
            with Path(path).open("rt", encoding="cp932") as reader:
                return list(reader)
        except UnicodeDecodeError:
            with Path(path).open("rt", encoding="utf-8", errors="replace") as reader:
                return list(reader)


def add_projected_mondo_associations(
    mondo_associations: AssociationMap,
    source_associations: AssociationMap,
    mondo_mapping: dict[str, list[str]],
) -> None:
    for key, sources in source_associations.items():
        disease_id, ncbi_id = key.split("\t")
        mondo_ids = mondo_mapping.get(disease_id)
        if mondo_ids is None:
            continue

        for mondo_id in mondo_ids:
            for source in sources:
                add_association(mondo_associations, mondo_id, ncbi_id, source)


def build_mondo_gene_associations(
    ncbigene_gene_info_path: str,
    mondo_owl_path: str,
    gencc_submissions_path: str,
    medgen_mim2gene_path: str,
    orphanet_product6_path: str,
) -> AssociationMap:
    gencc_associations = load_gencc_definitive_associations(
        ncbigene_gene_info_path,
        mondo_owl_path,
        gencc_submissions_path
    )
    mondo_mapping = load_mondo_mapping_from_owl(mondo_owl_path)
    omim_ncbi_gene_map = load_omim_gene_associations(medgen_mim2gene_path)
    # TODO:
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
    return mondo_ncbi_gene_map


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
    disease_namespace_in_path: str,
    disease_resource_prefix: str,
    disease_prefix_line: str,
    source_uri_map: dict[str, str],
) -> None:
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX ncbigene: <http://identifiers.org/ncbigene/>\n")
        writer.write(f"{disease_prefix_line}\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")
        writer.write("PREFIX sio: <http://semanticscience.org/resource/>\n")

        for key, sources in associations.items():
            disease_id, ncbi_id = key.split("\t")
            writer.write(
                "<https://pubcasefinder.dbcls.jp/gene_context/"
                f"disease:{disease_namespace_in_path}:{disease_id}/gene:ENT:{ncbi_id}>\n"
            )
            writer.write("    a sio:SIO_000983 ;\n")
            writer.write(
                f"    sio:SIO_000628 {disease_resource_prefix}{disease_id}, ncbigene:{ncbi_id} ;\n"
            )
            writer.write("    dcterms:source ")

            source_uris = [source_uri_map[source] for source in sources if source in source_uri_map]
            writer.write(", ".join(f"<{source_uri}>" for source_uri in source_uris))
            writer.write(" .\n")


def write_gencc_gene_association_ttl(
    output_path: str | Path,
    records: list[GenCCSubmissionRecord],
) -> None:
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
    graph.serialize(destination=str(output_path), format="turtle", encoding="utf-8")


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


def to_hpo_uri(hpo_curie: str | None) -> URIRef | None:
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
