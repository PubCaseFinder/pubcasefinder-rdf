from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import re
import fastobo

import duckdb
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

from package.rdf_build_support import (
    open_text_writer,
)


GENEREVIEWS = Namespace("https://www.ncbi.nlm.nih.gov/books/")
GTR = Namespace("https://www.ncbi.nlm.nih.gov/gtr/all/tests/?term=")
KEGG = Namespace("http://www.kegg.jp/entry/")
NANDO = Namespace("http://nanbyodata.jp/ontology/nando#")
NCIT = Namespace("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#")
MED2RDF = Namespace("http://med2rdf.org/ontology/")
MIM = Namespace("https://omim.org/entry/")
OBO = Namespace("http://purl.obolibrary.org/obo/")
ORDO = Namespace("http://www.orpha.net/ORDO/")

@dataclass
class DiseaseMappings:
    omim_to_mondo: dict[str, list[str]] = field(default_factory=dict)
    omim_to_umls: dict[str, list[str]] = field(default_factory=dict)
    orphanet_to_mondo: dict[str, str] = field(default_factory=dict)
    orphanet_to_omim: dict[str, str] = field(default_factory=dict)
    orphanet_to_umls: dict[str, list[str]] = field(default_factory=dict)
    orphanet_ids: list[str] = field(default_factory=list)
    _orphanet_id_set: set[str] = field(default_factory=set, repr=False)

    def add_orphanet_id(self, orphanet_id: str) -> None:
        if orphanet_id in self._orphanet_id_set:
            return
        self._orphanet_id_set.add(orphanet_id)
        self.orphanet_ids.append(orphanet_id)


@dataclass
class SharedReferenceData:
    inheritance_map: dict[str, list[str]]
    mappings: DiseaseMappings
    kegg_map: dict[str, str]
    gene_reviews_map: dict[str, list[str]]


@dataclass
class MondoExactMatches:
    mondo_id: str
    exact_matches: list[str] = field(default_factory=list)
    obsolete: bool = False


def add_value(mapping: dict[str, list[str]], key: str, value: str) -> None:
    values = mapping.setdefault(key, [])
    if value not in values:
        values.append(value)


def load_omim_disease_ids(path: str | Path) -> list[str]:
    omim_ids: list[str] = []
    seen: set[str] = set()

    con = duckdb.connect()
    query_statement = f"""
        select
            "# MIM Number"
        from
            read_csv('{path}', delim='\t')
        where
            "MIM Entry Type (see FAQ 1.3 at https://omim.org/help/faq)" in  (' ', 'phenotype', 'predominantly phenotypes')
        """
    res = con.execute(query_statement)

    while True:
        row = res.fetchone()
        if row is None:
            break
        row = str(row[0])
        if row not in seen:
            seen.add(row)
            omim_ids.append(row)
    return omim_ids

def load_omim_inheritance_map(path: str | Path) -> dict[str, list[str]]:
    inheritance_map: dict[str, list[str]] = {}

    con = duckdb.connect()
    query_statement = f"""
        select
            cast(MIM_number as varchar),
            replace(HPO_ID, 'HP:', '')
        from
            read_csv('{path}', delim='|')
        where
            relationship = 'inheritance_type_of'

        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()
        if row is None:
            break
        add_value(inheritance_map, row[0], row[1])
    return inheritance_map


def load_configured_disease_mappings(path: str | Path) -> DiseaseMappings:
    path = Path(path)
    if path.suffix.lower() == ".obo":
        return build_disease_mappings(iter_mondo_exact_matches_from_obo(path))
    return build_disease_mappings(iter_mondo_exact_matches_from_owl(path))


def load_shared_reference_data(
        medgene_omim_hpo_path,
        mondo_owl_path,
        kegg_disease_path,
        gene_review_path
) -> SharedReferenceData:
    return SharedReferenceData(
        inheritance_map=load_omim_inheritance_map(medgene_omim_hpo_path),
        mappings=load_configured_disease_mappings(mondo_owl_path),
        kegg_map=load_kegg_map(kegg_disease_path),
        gene_reviews_map=load_gene_reviews_map(gene_review_path),
    )


def load_disease_mappings_from_owl(mondo_owl_path: str | Path) -> DiseaseMappings:
    return build_disease_mappings(iter_mondo_exact_matches_from_owl(mondo_owl_path))


def load_disease_mappings_from_obo(mondo_obo_path: str | Path) -> DiseaseMappings:
    return build_disease_mappings(iter_mondo_exact_matches_from_obo(mondo_obo_path))


def build_disease_mappings(terms: Iterable[MondoExactMatches]) -> DiseaseMappings:
    mappings = DiseaseMappings()

    for term in terms:
        if term.obsolete:
            continue

        omim_ids: list[str] = []
        orphanet_ids: list[str] = []
        umls_ids: list[str] = []

        for exact_match in term.exact_matches:
            match extract_exact_match_id(exact_match):
                case ("omim", disease_id):
                    _append_unique(omim_ids, disease_id)
                case ("orphanet", disease_id):
                    _append_unique(orphanet_ids, disease_id)
                case ("umls", disease_id):
                    _append_unique(umls_ids, disease_id)

        finalize_mondo_term(
            mappings,
            term.mondo_id,
            omim_ids,
            orphanet_ids,
            umls_ids,
            obsolete=False,
        )

    return mappings


# graphのmondo_uri分、mondo_id, exactMatch対象, obsoleteのiteratorを返す
def iter_mondo_exact_matches_from_owl(mondo_owl_path: str | Path) -> Iterable[MondoExactMatches]:
    graph = Graph()
    graph.parse(str(mondo_owl_path), format="xml")

    mondo_uris = sorted(set(graph.subjects(SKOS.exactMatch, None)), key=str)
    for mondo_uri in mondo_uris:
        mondo_id = extract_mondo_id_from_uri(mondo_uri)
        if mondo_id is None:
            continue

        yield MondoExactMatches(
            mondo_id=mondo_id,
            exact_matches=[str(uri) for uri in sorted(graph.objects(mondo_uri, SKOS.exactMatch), key=str)],
            obsolete=any(str(value).strip().lower() == "true" for value in graph.objects(mondo_uri, OWL.deprecated))
        )

# oboのmondo_uri分、mondo_id, exactMatch対象, obsoleteのiteratorを返す
def iter_mondo_exact_matches_from_obo(mondo_obo_path: str | Path) -> Iterable[MondoExactMatches]:

    doc = fastobo.load(mondo_obo_path)
    for frame in doc:
        current_mondo_id = None
        current_is_deprecated = False
        exact_matches = []

        if frame.id.prefix == 'MONDO':
            current_mondo_id = frame.id.local
        for clause in frame:
            match clause.raw_tag():
                case 'is_obsolete':
                    if clause.raw_value() == 'true':
                        current_is_deprecated = True
                case 'xref':
                    exact_match = extract_equivalent_obo_xref(str(clause))
                    if exact_match is not None:
                        _append_unique(exact_matches, exact_match)
        if current_mondo_id is None:
            continue
        yield MondoExactMatches(
            mondo_id=current_mondo_id,
            exact_matches=exact_matches,
            obsolete=current_is_deprecated
        )



def finalize_mondo_term(
    mappings: DiseaseMappings,
    mondo_id: str | None,
    omim_ids: list[str],
    orphanet_ids: list[str],
    umls_ids: list[str],
    obsolete: bool,
) -> None:
    if obsolete or mondo_id is None:
        return

    for omim_id in omim_ids:
        add_value(mappings.omim_to_mondo, omim_id, mondo_id)
        for umls_id in umls_ids:
            add_value(mappings.omim_to_umls, omim_id, umls_id)

    for orphanet_id in orphanet_ids:
        mappings.add_orphanet_id(orphanet_id)
        mappings.orphanet_to_mondo.setdefault(orphanet_id, mondo_id)
        if len(omim_ids) == 1:
            mappings.orphanet_to_omim.setdefault(orphanet_id, omim_ids[0])
        for umls_id in umls_ids:
            add_value(mappings.orphanet_to_umls, orphanet_id, umls_id)


def extract_mondo_id_from_uri(uri: URIRef) -> str | None:
    match = re.search(r"/MONDO_(\d+)$", str(uri))
    return match.group(1) if match else None

def extract_equivalent_obo_xref(line: str) -> str | None:
    if not line.startswith("xref: ") or 'source="MONDO:equivalentTo"' not in line:
        return None

    match = re.match(r"^xref:\s+([^\s{!]+)", line)
    return match.group(1) if match else None


def extract_exact_match_id(uri: str) -> tuple[str, str] | None:
    patterns = (
        ("omim", r"(?:^OMIM:|omim\.org/entry/|/omim/)(\d+)"),
        ("orphanet", r"(?:^Orphanet:|Orphanet_)(\d+)"),
        ("umls", r"(?:^UMLS:|/id/)(C\d+)"),
    )

    for source, pattern in patterns:
        match = re.search(pattern, uri)
        if match:
            return source, match.group(1)
    return None


def load_kegg_map(path: str | Path) -> dict[str, str]:
    kegg_map: dict[str, str] = {}
    con = duckdb.connect()
    query_statement = f"""
        select
            *
        from read_csv('{path}', delim='\t')
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()
        if row is None:
            break
        kegg_map[str(row[0])] = row[1]
    return kegg_map

def load_gene_reviews_map(path: str | Path) -> dict[str, list[str]]:
    gene_reviews_map: dict[str, list[str]] = {}
    con = duckdb.connect()
    query_statement = f"""
        select
            *
        from read_csv('{path}', delim='\t')
        """
    res = con.execute(query_statement)
    while True:
        row = res.fetchone()
        if row is None:
            break
        add_value(gene_reviews_map, str(row[2]), str(row[0]))
    return gene_reviews_map


def write_omim_disease_ttl(
    output_path: str | Path,
    omim_ids: list[str],
    inheritance_map: dict[str, list[str]],
    mappings: DiseaseMappings,
    kegg_map: dict[str, str],
    gene_reviews_map: dict[str, list[str]],
) -> None:
    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("genereviews", GENEREVIEWS)
    graph.bind("gtr", GTR)
    graph.bind("kegg", KEGG)
    graph.bind("nando", NANDO)
    graph.bind("ncit", NCIT)
    graph.bind("med2rdf", MED2RDF)
    graph.bind("mim", MIM)
    graph.bind("obo", OBO)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)

    for omim_id in omim_ids:
        omim_id = str(omim_id)
        disease = MIM[omim_id]

        graph.add((disease, RDF.type, MED2RDF.Disease))
        graph.add((disease, RDF.type, NCIT.C7057))
        graph.add((disease, DCTERMS.identifier, Literal(omim_id)))

        for inheritance_id in inheritance_map.get(omim_id, []):
            graph.add((disease, NANDO.hasInheritance, OBO[f"HP_{inheritance_id}"]))

        for mondo_id in mappings.omim_to_mondo.get(omim_id, []):
            graph.add((disease, RDFS.seeAlso, OBO[f"MONDO_{mondo_id}"]))

        if omim_id in kegg_map:
            graph.add((disease, RDFS.seeAlso, KEGG[str(kegg_map[omim_id])]))

        for gene_review_id in gene_reviews_map.get(omim_id, []):
            graph.add((disease, RDFS.seeAlso, GENEREVIEWS[str(gene_review_id)]))

        for umls_id in mappings.omim_to_umls.get(omim_id, []):
            graph.add((disease, RDFS.seeAlso, GTR[str(umls_id)]))

    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format="turtle"))

def write_orphanet_disease_ttl(
    output_path: str | Path,
    mappings: DiseaseMappings,
    inheritance_map: dict[str, list[str]],
    kegg_map: dict[str, str],
    gene_reviews_map: dict[str, list[str]],
) -> None:

    graph = Graph()
    graph.bind("dcterms", DCTERMS)
    graph.bind("genereviews", GENEREVIEWS)
    graph.bind("gtr", GTR)
    graph.bind("kegg", KEGG)
    graph.bind("nando", NANDO)
    graph.bind("ncit", NCIT)
    graph.bind("med2rdf", MED2RDF)
    graph.bind("obo", OBO)
    graph.bind("ordo", ORDO)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)

    for orphanet_id in mappings.orphanet_ids:
        omim_id = mappings.orphanet_to_omim.get(orphanet_id)
        disease = ORDO[f'Orphanet_{orphanet_id}']

        graph.add((disease, RDF.type, MED2RDF.Disease))
        graph.add((disease, RDF.type, NCIT.C7057))
        graph.add((disease, DCTERMS.identifier, Literal(orphanet_id)))

        for inheritance_id in inheritance_map.get(omim_id, []):
            graph.add((disease, NANDO.hasInheritance, OBO[f'HP_{inheritance_id}']))
        if orphanet_id in mappings.orphanet_to_mondo:
            graph.add((disease, RDFS.seeAlso, OBO[f'MONDO_{mappings.orphanet_to_mondo[orphanet_id]}']))
        if omim_id is not None and omim_id in kegg_map:
            graph.add((disease, RDFS.seeAlso, KEGG[kegg_map[omim_id]]))
        for gene_review_id in gene_reviews_map.get(omim_id, []):
            graph.add((disease, RDFS.seeAlso, GENEREVIEWS[gene_review_id]))
        for uml_id in mappings.orphanet_to_umls.get(orphanet_id, []):
            graph.add((disease, RDFS.seeAlso, GTR[uml_id]))
    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format="turtle"))

def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
