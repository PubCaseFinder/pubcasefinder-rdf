from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import re
import fastobo

import duckdb
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, SKOS

from package.rdf_build_support import (
    load_config,
    open_text_reader,
    open_text_writer,
    resolve_configured_file,
    resolve_configured_output_dir,
    resolve_resource_root,
)


# CONFIG = load_config()

# OMIM_MIM2GENE_PATH = resolve_configured_file(
#     CONFIG,
#     "omim.mim2gene.path",
#     resolve_resource_root(CONFIG, "omim.dir"),
#     "mim2gene.txt",
# )
# MEDGEN_OMIM_HPO_PATH = resolve_configured_file(
#     CONFIG,
#     "medgen.omim.hpo.path",
#     resolve_resource_root(CONFIG, "medgen.dir"),
#     "MedGen_HPO_OMIM_Mapping.txt.gz",
#     alternate_file_names=("MedGen_HPO_OMIM_Mapping.txt",),
# )
# MONDO_OWL_PATH = resolve_configured_file(
#     CONFIG,
#     "mondo.owl.path",
#     resolve_resource_root(CONFIG, "mondo.dir"),
#     "mondo-international.owl",
#     alternate_file_names=("mondo.owl", "mondo.obo"),
# )
# KEGG_DISEASE_PATH = resolve_configured_file(
#     CONFIG,
#     "kegg.disease.path",
#     resolve_resource_root(CONFIG, "kegg.dir"),
#     "KEGG_disease.tsv",
# )
# GENE_REVIEWS_PATH = resolve_configured_file(
#     CONFIG,
#     "genereviews.omim.path",
#     resolve_resource_root(CONFIG, "genereviews.dir"),
#     "NBKid_shortname_OMIM.txt",
# )
# RDF_DIR = resolve_configured_output_dir(CONFIG)


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
        # TODO:
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
            obsolete=is_deprecated_resource(graph, mondo_uri),
        )


def iter_mondo_exact_matches_from_obo(mondo_obo_path: str | Path) -> Iterable[MondoExactMatches]:
    current_mondo_id: str | None = None
    current_is_deprecated = False
    exact_matches: list[str] = []

    def current_term() -> MondoExactMatches | None:
        if current_mondo_id is None:
            return None
        return MondoExactMatches(
            mondo_id=current_mondo_id,
            exact_matches=exact_matches,
            obsolete=current_is_deprecated,
        )

    with open_text_reader(mondo_obo_path) as reader:
        doc = fastobo.load(reader)
        for frame in doc:
            if frame.id.prefix == 'MONDO':
                
            

        # for raw_line in reader:
        #     line = raw_line.strip()
        #     if line == "[Term]" or (line.startswith("[") and line.endswith("]")):
        #         term = current_term()
        #         if term is not None:
        #             yield term
        #         current_mondo_id = None
        #         current_is_deprecated = False
        #         exact_matches = []
        #         continue

        #     if line.startswith("id: MONDO:"):
        #         mondo_id = line.removeprefix("id: MONDO:")
        #         current_mondo_id = mondo_id if mondo_id.isdigit() else None
        #         continue

        #     if current_mondo_id is None:
        #         continue

        #     if line == "is_obsolete: true":
        #         current_is_deprecated = True
        #         continue

        #     exact_match = extract_equivalent_obo_xref(line)
        #     if exact_match is not None:
        #         _append_unique(exact_matches, exact_match)

    term = current_term()
    if term is not None:
        yield term


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


def is_deprecated_resource(graph: Graph, uri: URIRef) -> bool:
    return any(str(value).strip().lower() == "true" for value in graph.objects(uri, OWL.deprecated))


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
    with open_text_reader(path) as reader:
        for line in reader:
            split = line.rstrip("\n").split("\t")
            if len(split) > 1 and split[0] not in kegg_map:
                kegg_map[split[0]] = split[1]
    return kegg_map


def load_gene_reviews_map(path: str | Path) -> dict[str, list[str]]:
    gene_reviews_map: dict[str, list[str]] = {}
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            split = line.rstrip("\n").split("\t")
            if len(split) > 2:
                add_value(gene_reviews_map, split[2], split[0])
    return gene_reviews_map


def write_omim_disease_ttl(
    output_path: str | Path,
    omim_ids: list[str],
    inheritance_map: dict[str, list[str]],
    mappings: DiseaseMappings,
    kegg_map: dict[str, str],
    gene_reviews_map: dict[str, list[str]],
) -> None:
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX genereviews: <https://www.ncbi.nlm.nih.gov/books/>\n")
        writer.write("PREFIX gtr: <https://www.ncbi.nlm.nih.gov/gtr/all/tests/?term=>\n")
        writer.write("PREFIX kegg: <http://www.kegg.jp/entry/>\n")
        writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>\n")
        writer.write("PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>\n")
        writer.write("PREFIX med2rdf: <http://med2rdf.org/ontology/>\n")
        writer.write("PREFIX mim: <https://omim.org/entry/>\n")
        writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")

        for omim_id in omim_ids:
            writer.write(f"mim:{omim_id}\n")
            writer.write("    a med2rdf:Disease, ncit:C7057 ;\n")
            writer.write(f'    dcterms:identifier "{omim_id}"')

            if omim_id in inheritance_map:
                writer.write(" ;\n")
                writer.write("    nando:hasInheritance ")
                _write_values(writer, "obo:HP_", inheritance_map[omim_id])
            if omim_id in mappings.omim_to_mondo:
                writer.write(" ;\n")
                writer.write("    rdfs:seeAlso ")
                _write_values(writer, "obo:MONDO_", mappings.omim_to_mondo[omim_id])
            if omim_id in kegg_map:
                writer.write(" ;\n")
                writer.write(f"    rdfs:seeAlso kegg:{kegg_map[omim_id]}")
            if omim_id in gene_reviews_map:
                writer.write(" ;\n")
                writer.write("    rdfs:seeAlso ")
                _write_values(writer, "genereviews:", gene_reviews_map[omim_id])
            if omim_id in mappings.omim_to_umls:
                writer.write(" ;\n")
                writer.write("    rdfs:seeAlso ")
                _write_values(writer, "gtr:", mappings.omim_to_umls[omim_id])
                writer.write(" .\n")
            else:
                writer.write(" .\n")


def write_orphanet_disease_ttl(
    output_path: str | Path,
    mappings: DiseaseMappings,
    inheritance_map: dict[str, list[str]],
    kegg_map: dict[str, str],
    gene_reviews_map: dict[str, list[str]],
) -> None:
    with open_text_writer(output_path) as writer:
        writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>\n")
        writer.write("PREFIX genereviews: <https://www.ncbi.nlm.nih.gov/books/>\n")
        writer.write("PREFIX gtr: <https://www.ncbi.nlm.nih.gov/gtr/all/tests/?term=>\n")
        writer.write("PREFIX kegg: <http://www.kegg.jp/entry/>\n")
        writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>\n")
        writer.write("PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>\n")
        writer.write("PREFIX med2rdf: <http://med2rdf.org/ontology/>\n")
        writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>\n")
        writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>\n")
        writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n")
        writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")

        for orphanet_id in mappings.orphanet_ids:
            omim_id = mappings.orphanet_to_omim.get(orphanet_id)
            writer.write(f"ordo:Orphanet_{orphanet_id}\n")
            writer.write("    a med2rdf:Disease, ncit:C7057 ;\n")
            writer.write(f'    dcterms:identifier "{orphanet_id}"')

            if omim_id is not None and omim_id in inheritance_map:
                writer.write(" ;\n")
                writer.write("    nando:hasInheritance ")
                _write_values(writer, "obo:HP_", inheritance_map[omim_id])
            if orphanet_id in mappings.orphanet_to_mondo:
                writer.write(" ;\n")
                writer.write(f"    rdfs:seeAlso obo:MONDO_{mappings.orphanet_to_mondo[orphanet_id]}")
            if omim_id is not None and omim_id in kegg_map:
                writer.write(" ;\n")
                writer.write(f"    rdfs:seeAlso kegg:{kegg_map[omim_id]}")
            if omim_id is not None and omim_id in gene_reviews_map:
                writer.write(" ;\n")
                writer.write("    rdfs:seeAlso ")
                _write_values(writer, "genereviews:", gene_reviews_map[omim_id])
            if orphanet_id in mappings.orphanet_to_umls:
                writer.write(" ;\n")
                writer.write("    rdfs:seeAlso ")
                _write_values(writer, "gtr:", mappings.orphanet_to_umls[orphanet_id])
                writer.write(" .\n")
            else:
                writer.write(" .\n")


def _write_values(writer, prefix: str, values: list[str], suffix: str = "") -> None:
    writer.write(", ".join(f"{prefix}{value}{suffix}" for value in values))


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
