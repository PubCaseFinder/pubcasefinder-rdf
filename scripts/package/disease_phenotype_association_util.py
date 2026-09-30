from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import duckdb
from rdflib import Graph, Literal, Namespace, URIRef, BNode
from rdflib.namespace import DCTERMS, RDF, RDFS, FOAF

from utils.log_util import get_logger
from package.rdf_build_support import (
    open_text_writer,
)

logger = get_logger()

HPOA_SOURCE = "phenotype.hpoa"
HPOA_PAGE = 'https://hpo.jax.org/data/annotations'

ORDO_FREQUENCY_TO_HPO = {
    "Obligate (100%)": "0040280",
    "Very frequent (99-80%)": "0040281",
    "Frequent (79-30%)": "0040282",
    "Occasional (29-5%)": "0040283",
    "Very rare (<4-1%)": "0040284",
    "Excluded (0%)": "0040285",
}

OA = Namespace('http://www.w3.org/ns/oa#')
OBO = Namespace("http://purl.obolibrary.org/obo/")
HOOM = Namespace("http://www.semanticweb.org/ontology/HOOM#")
ORDO = Namespace("http://www.orpha.net/ORDO/")
HPOA = Namespace('http://compbio.charite.de/jenkins/job/hpo.annotations.current/lastSuccessfulBuild/artifact/current/')

@dataclass
class AnnotationSource:
    source: str
    creator: str
    page: str


@dataclass
class OrdoPhenotypeAnnotation:
    ordo_id: str
    hpo_id: str
    frequency_term_id: str | None


def load_ordo_frequency_annotations(orphanet_product4_path: str | Path) -> dict[str, str]:
    logger.info("loading Orphanet frequency annotations: path=%s", orphanet_product4_path)
    frequencies: dict[str, str] = {}
    tree = ET.parse(orphanet_product4_path)
    root = tree.getroot()

    for disorder_list in root.iter("HPODisorderSetStatusList"):
        for disorder in disorder_list.iter("Disorder"):
            orpha_code = disorder.find(".//OrphaCode")
            if orpha_code is None or orpha_code.text is None:
                continue

            for association in disorder.findall(".//HPODisorderAssociation"):
                hpo_id_element = association.find(".//HPOId")
                if hpo_id_element is None or hpo_id_element.text is None:
                    continue

                hpo_frequency_element = association.find(".//HPOFrequency")
                frequency_label = extract_frequency_label(hpo_frequency_element)
                if frequency_label is None:
                    continue

                key = f"{orpha_code.text.strip()}\t{normalize_hpo_id(hpo_id_element.text)}"
                # Prefer a positive frequency if duplicate source records conflict.
                if (frequencies.get(key) == "Excluded (0%)"
                        and frequency_label in ORDO_FREQUENCY_TO_HPO
                        and frequency_label != "Excluded (0%)"):
                    frequencies[key] = frequency_label
                else:
                    frequencies.setdefault(key, frequency_label)

    logger.info("loaded Orphanet frequency annotations: path=%s annotations=%s", orphanet_product4_path, len(frequencies))
    return frequencies


def load_manual_phenotype_associations(
    phenotype_hpoa_path: str | Path,
    disease_prefix: str,
) -> dict[str, str]:
    logger.info(
        "loading manual phenotype associations: path=%s disease_prefix=%s",
        phenotype_hpoa_path,
        disease_prefix,
    )
    manual_associations: dict[str, str] = {}
    prefix = f"{disease_prefix}:"

    # Only leading metadata is a comment; disease names can contain literal '#'.
    skip_rows = 0
    with Path(phenotype_hpoa_path).open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.startswith("#") or not line.strip():
                skip_rows += 1
            else:
                break
    query_statement = """
        select
            trim(database_id),
            trim(hpo_id),
            coalesce(trim(qualifier), ''),
            coalesce(trim(frequency), '')
        from
            read_csv(?, delim='\t', header=true, skip=?, all_varchar=true)
        where
            starts_with(trim(database_id), ?)
        """
    excluded_rows = 0
    with duckdb.connect() as con:
        res = con.execute(query_statement, [str(phenotype_hpoa_path), skip_rows, prefix])
        while (row := res.fetchone()) is not None:
            database_id, hpo_id, qualifier, frequency = row
            if qualifier == "NOT":
                excluded_rows += 1
                continue
            if qualifier:
                raise ValueError(f"Unexpected HPOA qualifier for {database_id} / {hpo_id}: {qualifier!r}")
            try:
                absent = is_zero_frequency(frequency)
            except ValueError as exc:
                raise ValueError(f"Invalid HPOA frequency for {database_id} / {hpo_id}: {frequency!r}") from exc
            if absent:
                excluded_rows += 1
                continue
            # Filter records before deduplication: an independent positive row survives.
            key = f"{database_id.removeprefix(prefix)}\t{normalize_hpo_id(hpo_id)}"
            manual_associations.setdefault(key, "Manual")

    logger.info(
        "loaded manual phenotype associations: path=%s disease_prefix=%s associations=%s excluded_rows=%s",
        phenotype_hpoa_path,
        disease_prefix,
        len(manual_associations),
        excluded_rows,
    )
    return manual_associations


def is_zero_frequency(frequency: str) -> bool:
    """Recognize absence without treating an unspecified frequency as zero."""
    frequency = frequency.strip()
    if not frequency:
        return False
    if frequency in {f"HP:{term}" for term in ORDO_FREQUENCY_TO_HPO.values()}:
        return frequency == "HP:0040285"
    fraction = re.fullmatch(r"(\d+)/(\d+)", frequency)
    if fraction:
        count, total = map(int, fraction.groups())
        if total > 0 and count <= total:
            return count == 0
    percentage = re.fullmatch(r"(\d+(?:\.\d+)?)%", frequency)
    if percentage:
        value = Decimal(percentage.group(1))
        if value <= 100:
            return value == 0
    raise ValueError(f"Invalid HPOA frequency: {frequency!r}")


def extract_frequency_label(hpo_frequency_element: ET.Element | None) -> str | None:
    if hpo_frequency_element is None:
        return None

    name = hpo_frequency_element.find("Name")
    if name is None or name.text is None:
        return None
    return name.text.strip()


def normalize_hpo_id(value: str) -> str:
    return value.strip().replace("HP:", "")


def create_annotation_source(source: str, creator: str, page: str) -> AnnotationSource:
    logger.info("creating annotation source: source=%s creator=%s page=%s", source, creator, page)
    return AnnotationSource(source=source, creator=creator, page=page)


def write_ordo_phenotype_association_ttl(
    output_path: str | Path,
    manual_associations: dict[str, str],
    frequency_by_association: dict[str, str],
    source: AnnotationSource,
) -> None:
    logger.info(
        "writing Orphanet phenotype association TTL: output=%s manual_associations=%s frequencies=%s",
        output_path,
        len(manual_associations),
        len(frequency_by_association),
    )
    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("foaf", FOAF)
    graph.bind("hoom", HOOM)
    graph.bind("oa", OA)
    graph.bind("obo", OBO)
    graph.bind("ordo", ORDO)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("hpoa", HPOA)

    source_creator = source.creator
    source_page = URIRef(source.page)
    source_node = HPOA[source.source]
    graph.add((source_node, DCTERMS.creator, Literal(source_creator)))
    graph.add((source_node, FOAF.page, source_page))
    for annotation in build_ordo_annotations(manual_associations, frequency_by_association):

        disease = URIRef(
            "https://pubcasefinder.dbcls.jp/phenotype_context/"
            f"disease:ORDO:{annotation.ordo_id}/phenotype:HP:{annotation.hpo_id}"
        )

        graph.add((disease, RDF.type, OA.Annotation))
        graph.add((disease, OA.hasTarget, ORDO[f"Orphanet_{annotation.ordo_id}"]))
        graph.add((disease, OA.hasBody, OBO[f"HP_{annotation.hpo_id}"]))
        if annotation.frequency_term_id is not None:
            graph.add((disease, HOOM.with_frequency, OBO[f"HP_{annotation.frequency_term_id}"]))
        graph.add((disease, DCTERMS.source, source_node))
        graph.add((disease, OBO["ECO_9000001"], OBO["ECO_0000218"]))


    for label, hpo_id in ORDO_FREQUENCY_TO_HPO.items():
        graph.add((OBO[f"HP_{hpo_id}"], RDFS.label, Literal(label, lang="en")))

    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format='turtle'))
    logger.info("finished writing Orphanet phenotype association TTL: output=%s triples=%s", output_path, len(graph))


def write_manual_phenotype_association_ttl(
    output_path: str | Path,
    disease_namespace_in_path: str,
    disease_resource_prefix: str,
    disease_resource_prefix_uri: str,
    manual_associations: dict[str, str],
    source: AnnotationSource,
) -> None:

    logger.info(
        "writing manual phenotype association TTL: output=%s disease_namespace=%s associations=%s",
        output_path,
        disease_namespace_in_path,
        len(manual_associations),
    )
    disease_namespace = Namespace(disease_resource_prefix_uri)

    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("foaf", FOAF)
    graph.bind(disease_resource_prefix, disease_namespace)
    graph.bind("oa", OA)
    graph.bind("obo", OBO)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("hpoa", HPOA)


    source_creator = source.creator
    source_page = URIRef(source.page)
    source_node = HPOA[source.source]
    graph.add((source_node, DCTERMS.creator, Literal(source_creator)))
    graph.add((source_node, FOAF.page, URIRef(source_page)))
    for key in manual_associations:
        disease_id, hpo_id = key.split("\t")

        disease = URIRef(f'https://pubcasefinder.dbcls.jp/phenotype_context/disease:{disease_namespace_in_path}:{disease_id}/phenotype:HP:{hpo_id}')

        graph.add((disease, RDF.type, OA.Annotation))
        graph.add((disease, OA.hasTarget, disease_namespace[disease_id]))
        graph.add((disease, OA.hasBody, OBO[f'HP_{hpo_id}']))
        graph.add((disease, DCTERMS.source, source_node))
        graph.add((disease, OBO['ECO_9000001'], OBO['ECO_0000218']))

    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format='turtle'))
    logger.info("finished writing manual phenotype association TTL: output=%s triples=%s", output_path, len(graph))

def build_ordo_annotations(
    manual_associations: dict[str, str],
    frequency_by_association: dict[str, str],
) -> list[OrdoPhenotypeAnnotation]:
    logger.info(
        "building Orphanet phenotype annotations: manual_associations=%s frequencies=%s",
        len(manual_associations),
        len(frequency_by_association),
    )
    annotations: list[OrdoPhenotypeAnnotation] = []
    for key in manual_associations:
        ordo_id, hpo_id = key.split("\t")
        frequency_label = frequency_by_association.get(key)
        if frequency_label == "Excluded (0%)":
            # Membership comes from filtered HPOA positives; product 4 only adds frequency.
            logger.warning(
                "Orphanet frequency conflicts with positive HPOA association: ORPHA:%s HP:%s; omitting frequency",
                ordo_id, hpo_id,
            )
            frequency_label = None
        annotations.append(
            OrdoPhenotypeAnnotation(
                ordo_id=ordo_id,
                hpo_id=hpo_id,
                frequency_term_id=ORDO_FREQUENCY_TO_HPO.get(frequency_label),
            )
        )
    logger.info("built Orphanet phenotype annotations: annotations=%s", len(annotations))
    return annotations


def write_frequency_labels(writer) -> None:
    logger.info("writing Orphanet frequency labels: labels=%s", len(ORDO_FREQUENCY_TO_HPO))
    for label, hpo_id in ORDO_FREQUENCY_TO_HPO.items():
        writer.write(f"obo:HP_{hpo_id}\n")
        writer.write(f'    rdfs:label "{label}"@en .\n')
    logger.info("finished writing Orphanet frequency labels")
