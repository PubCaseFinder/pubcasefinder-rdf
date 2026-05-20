from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import csv
import re
import xml.etree.ElementTree as ET

from scripts.package.rdf_build_support import (
    load_config,
    open_text_reader,
    open_text_writer,
    resolve_configured_file,
    resolve_configured_output_dir,
    resolve_resource_root,
)


GENCC_SOURCE_URI = "https://search.thegencc.org/download/action/submissions-export-csv"

CONFIG = load_config()

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
    gencc_id: str
    ncbi_gene_id: str
    disease_curie: str
    classification_title: str
    moi_curie: str | None
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
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            split = line.rstrip("\n").split("\t")
            if len(split) > 2 and split[2] not in ncbi_gene_symbol_map:
                ncbi_gene_symbol_map[split[2]] = split[1]
    return ncbi_gene_symbol_map


def load_hgnc_to_ncbi_map(path: str | Path) -> dict[str, str]:
    hgnc_to_ncbi_map: dict[str, str] = {}
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            split = line.rstrip("\n").split("\t")
            if len(split) <= 5:
                continue

            hgnc_id = extract_hgnc_id(split[5])
            if hgnc_id is not None and hgnc_id not in hgnc_to_ncbi_map:
                hgnc_to_ncbi_map[hgnc_id] = split[1]
    return hgnc_to_ncbi_map


def load_gencc_submission_records(
    gencc_submissions_path: str | Path = GENCC_SUBMISSIONS_PATH,
    ncbi_gene_info_path: str | Path = NCBI_GENE_INFO_PATH,
) -> list[GenCCSubmissionRecord]:
    hgnc_to_ncbi_map = load_hgnc_to_ncbi_map(ncbi_gene_info_path)
    records: list[GenCCSubmissionRecord] = []

    with open_text_reader(gencc_submissions_path) as reader:
        delimiter = "," if str(gencc_submissions_path).lower().endswith(".csv") else "\t"
        rows = csv.reader(reader, delimiter=delimiter)
        next(rows, None)
        for split in rows:
            if len(split) <= 19:
                continue

            gencc_id = normalize_value(split[0])
            hgnc_id = normalize_curie_value(split[1], "HGNC:")
            disease_curie = normalize_value(split[5])
            classification_title = normalize_value(split[8]) or ""
            moi_curie = normalize_moi_curie(normalize_value(split[9]))
            submitter_id = normalize_value(split[19])

            if gencc_id is None or hgnc_id is None or disease_curie is None or ":" not in disease_curie:
                continue

            ncbi_gene_id = hgnc_to_ncbi_map.get(hgnc_id)
            if ncbi_gene_id is None:
                continue

            records.append(
                GenCCSubmissionRecord(
                    gencc_id=gencc_id,
                    ncbi_gene_id=ncbi_gene_id,
                    disease_curie=disease_curie,
                    classification_title=classification_title,
                    moi_curie=moi_curie,
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
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            try:
                split = line.rstrip("\n").split("\t")
                if len(split) > 2 and split[2] == "phenotype" and split[1] != "-":
                    add_association(associations, split[0], split[1], "MedGen")
            except Exception:
                continue
    return associations


def load_gencc_definitive_associations() -> GenCCAssociations:
    return load_gencc_associations({"GENCC:100001"}, project_mondo_to_mapped_diseases=True)


def load_gencc_associations(
    allowed_classification_curies: set[str] | None,
    *,
    project_mondo_to_mapped_diseases: bool,
) -> GenCCAssociations:
    hgnc_to_ncbi_map = load_hgnc_to_ncbi_map(NCBI_GENE_INFO_PATH)
    mondo_mapping = load_configured_mondo_mapping()
    associations = GenCCAssociations()

    with open_text_reader(GENCC_SUBMISSIONS_PATH) as reader:
        delimiter = "," if str(GENCC_SUBMISSIONS_PATH).lower().endswith(".csv") else "\t"
        rows = csv.reader(reader, delimiter=delimiter)
        next(rows, None)
        for split in rows:
            if len(split) <= 7:
                continue

            hgnc_id = normalize_curie_value(split[1], "HGNC:")
            disease_curie = normalize_value(split[3])
            original_disease_curie = normalize_value(split[5])
            classification_curie = normalize_value(split[7])

            if allowed_classification_curies is not None and classification_curie not in allowed_classification_curies:
                continue

            ncbi_id = hgnc_to_ncbi_map.get(hgnc_id)
            if ncbi_id is None:
                continue

            if original_disease_curie and ":" in original_disease_curie:
                add_original_disease_association(associations, ncbi_id, original_disease_curie)
            elif disease_curie is not None and disease_curie.startswith("MONDO:"):
                add_association(
                    associations.mondo_associations,
                    normalize_curie_value(disease_curie, "MONDO:"),
                    ncbi_id,
                    "GenCC",
                )

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


def load_configured_mondo_mapping() -> MondoMapping:
    path = Path(MONDO_OWL_PATH)
    if path.suffix.lower() == ".obo":
        return load_mondo_mapping_from_obo(path)
    return load_mondo_mapping_from_owl(path)


def load_mondo_mapping_from_owl(mondo_owl_path: str | Path) -> MondoMapping:
    mapping = MondoMapping()
    current_mondo_id: str | None = None
    current_is_deprecated = False
    current_class_depth = 0

    with open_text_reader(mondo_owl_path) as reader:
        for line in reader:
            trimmed = line.strip()

            if current_mondo_id is not None:
                if (
                    trimmed
                    == '<owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>'
                ):
                    current_is_deprecated = True
                elif not current_is_deprecated and trimmed.startswith('<skos:exactMatch rdf:resource="'):
                    exact_match_uri = extract_uri_value(trimmed)
                    if exact_match_uri is not None:
                        omim_id = extract_omim_id(exact_match_uri)
                        if omim_id is not None:
                            add_to_mapping(mapping.mondo_to_omim, current_mondo_id, omim_id)
                            add_to_mapping(mapping.omim_to_mondo, omim_id, current_mondo_id)

                        orpha_id = extract_orphanet_id(exact_match_uri)
                        if orpha_id is not None:
                            add_to_mapping(mapping.mondo_to_orpha, current_mondo_id, orpha_id)
                            add_to_mapping(mapping.orpha_to_mondo, orpha_id, current_mondo_id)

                current_class_depth += trimmed.count("<owl:Class")
                current_class_depth -= trimmed.count("</owl:Class>")
                if current_class_depth <= 0:
                    current_mondo_id = None
                    current_is_deprecated = False
                    current_class_depth = 0
                continue

            if not trimmed.startswith('<owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_'):
                continue

            current_mondo_id = extract_mondo_id_from_uri_line(trimmed)
            current_is_deprecated = False
            current_class_depth = 1

    return mapping


def load_mondo_mapping_from_obo(mondo_obo_path: str | Path) -> MondoMapping:
    mapping = MondoMapping()
    current_mondo_id: str | None = None
    current_is_deprecated = False

    def flush_term() -> None:
        return None

    with open_text_reader(mondo_obo_path) as reader:
        for raw_line in reader:
            line = raw_line.strip()
            if line == "[Term]":
                flush_term()
                current_mondo_id = None
                current_is_deprecated = False
                continue
            if line.startswith("[") and line.endswith("]"):
                flush_term()
                current_mondo_id = None
                current_is_deprecated = False
                continue

            if line.startswith("id: MONDO:"):
                mondo_id = line.removeprefix("id: MONDO:")
                current_mondo_id = mondo_id if mondo_id.isdigit() else None
                current_is_deprecated = False
                continue

            if current_mondo_id is None:
                continue

            if line == "is_obsolete: true":
                current_is_deprecated = True
                continue

            if current_is_deprecated:
                continue
            if not line.startswith("xref: ") or 'source="MONDO:equivalentTo"' not in line:
                continue

            omim_match = re.match(r"^xref: OMIM:(\d+)\b", line)
            if omim_match:
                omim_id = omim_match.group(1)
                add_to_mapping(mapping.mondo_to_omim, current_mondo_id, omim_id)
                add_to_mapping(mapping.omim_to_mondo, omim_id, current_mondo_id)
                continue

            orpha_match = re.match(r"^xref: Orphanet:(\d+)\b", line)
            if orpha_match:
                orpha_id = orpha_match.group(1)
                add_to_mapping(mapping.mondo_to_orpha, current_mondo_id, orpha_id)
                add_to_mapping(mapping.orpha_to_mondo, orpha_id, current_mondo_id)

    flush_term()
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


def build_mondo_gene_associations() -> AssociationMap:
    gencc_associations = load_gencc_definitive_associations()
    mondo_mapping = load_configured_mondo_mapping()
    omim_ncbi_gene_map = load_omim_gene_associations(MEDGEN_MIM2GENE_PATH)
    orphanet_ncbi_gene_map = load_orphanet_gene_associations(NCBI_GENE_INFO_PATH, ORPHANET_PRODUCT6_PATH)

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
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX gencc: <https://search.thegencc.org/submissions/>\n")
        writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>\n")
        writer.write("PREFIX ncbigene: <http://identifiers.org/ncbigene/>\n")
        writer.write("PREFIX mim: <https://omim.org/entry/>\n")
        writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>\n")
        writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")
        writer.write("PREFIX sio: <http://semanticscience.org/resource/>\n")

        for record in records:
            disease_path = to_disease_path_segment(record.disease_curie)
            disease_resource = to_disease_resource(record.disease_curie)

            if (
                disease_path is None
                or disease_resource is None
                or record.ncbi_gene_id is None
                or record.gencc_id is None
            ):
                continue

            writer.write(
                "<https://pubcasefinder.dbcls.jp/gene_context/"
                f"disease:{disease_path}/gene:ENT:{record.ncbi_gene_id}>\n"
            )
            writer.write("    a sio:SIO_000983 ;\n")
            writer.write(
                f"    sio:SIO_000628 {disease_resource}, ncbigene:{record.ncbi_gene_id} ;\n"
            )
            writer.write(f"    dcterms:source gencc:{record.gencc_id} .\n")
            writer.write(f"gencc:{record.gencc_id}\n")
            writer.write(f'    obo:IAO_0000114 "{escape_turtle_literal(record.classification_title)}" ;\n')
            if record.moi_curie:
                writer.write(f"    nando:hasInheritance obo:{record.moi_curie} ;\n")
            writer.write(f'    dcterms:creator "{escape_turtle_literal(record.submitter_label)}" .\n')


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


def normalize_moi_curie(moi_curie: str | None) -> str | None:
    if not moi_curie:
        return None
    return moi_curie.replace(":", "_")


def resolve_gencc_submitter_label(submitter_id: str | None) -> str:
    if submitter_id is None:
        return ""
    return GENCC_SUBMITTER_LABELS.get(submitter_id, submitter_id)


def escape_turtle_literal(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def to_disease_path_segment(disease_curie: str | None) -> str | None:
    if disease_curie is None:
        return None
    if disease_curie.startswith("Orphanet:"):
        return "ORDO:" + normalize_curie_value(disease_curie, "Orphanet:")
    return disease_curie


def to_disease_resource(disease_curie: str | None) -> str | None:
    if disease_curie is None:
        return None
    if disease_curie.startswith("OMIM:"):
        return "mim:" + normalize_curie_value(disease_curie, "OMIM:")
    if disease_curie.startswith("Orphanet:"):
        return "ordo:Orphanet_" + normalize_curie_value(disease_curie, "Orphanet:")
    if disease_curie.startswith("MONDO:"):
        return "obo:MONDO_" + normalize_curie_value(disease_curie, "MONDO:")
    return None


def add_to_mapping(mapping: dict[str, list[str]], key: str, value: str) -> None:
    values = mapping.setdefault(key, [])
    if value not in values:
        values.append(value)


def extract_mondo_id_from_uri_line(line: str) -> str | None:
    marker = "http://purl.obolibrary.org/obo/MONDO_"
    start = line.find(marker)
    if start < 0:
        return None

    value_start = start + len(marker)
    value_end = value_start
    while value_end < len(line) and line[value_end].isdigit():
        value_end += 1
    return line[value_start:value_end] if value_end > value_start else None


def extract_uri_value(line: str) -> str | None:
    prefix = 'rdf:resource="'
    start = line.find(prefix)
    if start < 0:
        return None

    value_start = start + len(prefix)
    value_end = line.find('"', value_start)
    return line[value_start:value_end] if value_end > value_start else None


def extract_omim_id(uri: str) -> str | None:
    for marker in ("/omim/", "omim.org/entry/"):
        start = uri.find(marker)
        if start < 0:
            continue

        start += len(marker)
        end = start
        while end < len(uri) and uri[end].isdigit():
            end += 1
        if end > start:
            return uri[start:end]
    return None


def extract_orphanet_id(uri: str) -> str | None:
    marker = "Orphanet_"
    start = uri.find(marker)
    if start < 0:
        return None

    start += len(marker)
    end = start
    while end < len(uri) and uri[end].isdigit():
        end += 1
    return uri[start:end] if end > start else None
