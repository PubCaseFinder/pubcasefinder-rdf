from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.package.rdf_build_support import (
    load_config,
    open_text_reader,
    open_text_writer,
    resolve_configured_file,
    resolve_configured_output_dir,
    resolve_resource_root,
)


CONFIG = load_config()

ORPHANET_PRODUCT4_PATH = resolve_configured_file(
    CONFIG,
    "orphanet.product4.path",
    resolve_resource_root(CONFIG, "orphanet.dir"),
    "en_product4.xml",
)
HPO_PHENOTYPE_PATH = resolve_configured_file(
    CONFIG,
    "hpo.phenotype.path",
    resolve_resource_root(CONFIG, "hpo.dir"),
    "phenotype.hpoa",
)
RDF_DIR = resolve_configured_output_dir(CONFIG)
HPOA_SOURCE_URI = (
    "http://compbio.charite.de/jenkins/job/hpo.annotations.current/"
    "lastSuccessfulBuild/artifact/current/phenotype.hpoa"
)

ORDO_FREQUENCY_TO_HPO = {
    "Obligate (100%)": "0040280",
    "Very frequent (99-80%)": "0040281",
    "Frequent (79-30%)": "0040282",
    "Occasional (29-5%)": "0040283",
    "Very rare (<4-1%)": "0040284",
    "Excluded (0%)": "0040285",
}


@dataclass
class AnnotationSource:
    creator: str
    page: str


@dataclass
class OrdoPhenotypeAnnotation:
    ordo_id: str
    hpo_id: str
    frequency_term_id: str | None


def load_ordo_frequency_annotations(orphanet_product4_path: str | Path) -> dict[str, str]:
    frequencies: dict[str, str] = {}
    tree = ET.parse(orphanet_product4_path)
    root = tree.getroot()

    for disorder_list in root.iter("HPODisorderSetStatusList"):
        for disorder in disorder_list.iter("Disorder"):
            orpha_code = disorder.find("OrphaCode")
            if orpha_code is None or orpha_code.text is None:
                continue

            hpo_ids = disorder.findall(".//HPOId")
            hpo_frequencies = disorder.findall(".//HPOFrequency")
            for hpo_id_element, hpo_frequency_element in zip(hpo_ids, hpo_frequencies):
                if hpo_id_element.text is None:
                    continue

                frequency_label = extract_frequency_label(hpo_frequency_element)
                if frequency_label is None:
                    continue

                key = f"{orpha_code.text.strip()}\t{normalize_hpo_id(hpo_id_element.text)}"
                frequencies.setdefault(key, frequency_label)

    return frequencies


def load_manual_phenotype_associations(
    phenotype_hpoa_path: str | Path,
    disease_prefix: str,
) -> dict[str, str]:
    manual_associations: dict[str, str] = {}
    prefix = f"{disease_prefix}:"

    with open_text_reader(phenotype_hpoa_path) as reader:
        for line in reader:
            if line.startswith("#"):
                continue

            split = line.rstrip("\n").split("\t")
            if len(split) <= 3 or not split[0].startswith(prefix):
                continue

            disease_id = split[0][len(prefix) :].strip()
            hpo_id = normalize_hpo_id(split[3])
            key = f"{disease_id}\t{hpo_id}"
            manual_associations.setdefault(key, "Manual")

    return manual_associations


def extract_frequency_label(hpo_frequency_element: ET.Element | None) -> str | None:
    if hpo_frequency_element is None:
        return None

    name = hpo_frequency_element.find("Name")
    if name is None or name.text is None:
        return None
    return name.text.strip()


def normalize_hpo_id(value: str) -> str:
    return value.strip().replace("HP:", "")


def create_annotation_source(creator: str, page: str) -> AnnotationSource:
    return AnnotationSource(creator=creator, page=page)


def write_ordo_phenotype_association_ttl(
    output_path: str | Path,
    manual_associations: dict[str, str],
    frequency_by_association: dict[str, str],
    source: AnnotationSource,
) -> None:
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX foaf: <http://xmlns.com/foaf/0.1>\n")
        writer.write("PREFIX hoom: <http://www.semanticweb.org/ontology/HOOM#>\n")
        writer.write("PREFIX oa: <http://www.w3.org/ns/oa#>\n")
        writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>\n")
        writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")

        blank_node_counter = 0
        for annotation in build_ordo_annotations(manual_associations, frequency_by_association):
            blank_node_counter += 1
            writer.write(
                "<https://pubcasefinder.dbcls.jp/phenotype_context/"
                f"disease:ORDO:{annotation.ordo_id}/phenotype:HP:{annotation.hpo_id}>\n"
            )
            writer.write("    a oa:Annotation ;\n")
            writer.write(f"    oa:hasTarget ordo:Orphanet_{annotation.ordo_id} ;\n")
            writer.write(f"    oa:hasBody obo:HP_{annotation.hpo_id} ;\n")
            if annotation.frequency_term_id is not None:
                writer.write(f"    hoom:with_frequency obo:HP_{annotation.frequency_term_id} ;\n")
            writer.write(f"    dcterms:source _:b{blank_node_counter} ;\n")
            writer.write("    obo:ECO_9000001 obo:ECO_0000218 .\n")

            writer.write(f"_:b{blank_node_counter}\n")
            writer.write(f'    dcterms:creator "{source.creator}" ;\n')
            writer.write(f"    foaf:page <{source.page}> .\n")

        write_frequency_labels(writer)


def write_manual_phenotype_association_ttl(
    output_path: str | Path,
    disease_namespace_in_path: str,
    disease_resource_prefix: str,
    disease_prefix_line: str,
    manual_associations: dict[str, str],
    source: AnnotationSource,
) -> None:
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX foaf: <http://xmlns.com/foaf/0.1>\n")
        writer.write(f"{disease_prefix_line}\n")
        writer.write("PREFIX oa: <http://www.w3.org/ns/oa#>\n")
        writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")

        blank_node_counter = 0
        for key in manual_associations:
            disease_id, hpo_id = key.split("\t")
            blank_node_counter += 1

            writer.write(
                "<https://pubcasefinder.dbcls.jp/phenotype_context/"
                f"disease:{disease_namespace_in_path}:{disease_id}/phenotype:HP:{hpo_id}>\n"
            )
            writer.write("    a oa:Annotation ;\n")
            writer.write(f"    oa:hasTarget {disease_resource_prefix}{disease_id} ;\n")
            writer.write(f"    oa:hasBody obo:HP_{hpo_id} ;\n")
            writer.write(f"    dcterms:source _:b{blank_node_counter} ;\n")
            writer.write("    obo:ECO_9000001 obo:ECO_0000218 .\n")

            writer.write(f"_:b{blank_node_counter}\n")
            writer.write(f'    dcterms:creator "{source.creator}" ;\n')
            writer.write(f"    foaf:page <{source.page}> .\n")


def build_ordo_annotations(
    manual_associations: dict[str, str],
    frequency_by_association: dict[str, str],
) -> list[OrdoPhenotypeAnnotation]:
    annotations: list[OrdoPhenotypeAnnotation] = []
    for key in manual_associations:
        ordo_id, hpo_id = key.split("\t")
        frequency_label = frequency_by_association.get(key)
        annotations.append(
            OrdoPhenotypeAnnotation(
                ordo_id=ordo_id,
                hpo_id=hpo_id,
                frequency_term_id=ORDO_FREQUENCY_TO_HPO.get(frequency_label),
            )
        )
    return annotations


def write_frequency_labels(writer) -> None:
    for label, hpo_id in ORDO_FREQUENCY_TO_HPO.items():
        writer.write(f"obo:HP_{hpo_id}\n")
        writer.write(f'    rdfs:label "{label}"@en .\n')
