from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import duckdb

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

    i = 0
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
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            split = line.rstrip("\n").split("|")
            if len(split) <= 5:
                continue
            if split[3] == "inheritance_type_of":
                add_value(inheritance_map, split[1], split[5].replace("HP:", ""))
    return inheritance_map


def load_configured_disease_mappings() -> DiseaseMappings:
    return load_disease_mappings(MONDO_OWL_PATH)


def load_shared_reference_data() -> SharedReferenceData:
    return SharedReferenceData(
        inheritance_map=load_omim_inheritance_map(MEDGEN_OMIM_HPO_PATH),
        mappings=load_configured_disease_mappings(),
        kegg_map=load_kegg_map(KEGG_DISEASE_PATH),
        gene_reviews_map=load_gene_reviews_map(GENE_REVIEWS_PATH),
    )


def load_disease_mappings(path: str | Path) -> DiseaseMappings:
    path = Path(path)
    if path.suffix.lower() == ".obo":
        return load_disease_mappings_from_obo(path)
    return load_disease_mappings_from_owl(path)


def load_disease_mappings_from_owl(mondo_owl_path: str | Path) -> DiseaseMappings:
    mappings = DiseaseMappings()
    current_mondo_id: str | None = None
    current_is_deprecated = False
    current_class_depth = 0
    omim_ids: list[str] = []
    orphanet_ids: list[str] = []
    umls_ids: list[str] = []

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
                        omim_id = extract_id_from_uri(exact_match_uri, "/entry/")
                        if omim_id is not None and omim_id.isdigit():
                            _append_unique(omim_ids, omim_id)

                        orphanet_id = extract_id_from_uri(exact_match_uri, "Orphanet_")
                        if orphanet_id is not None and orphanet_id.isdigit():
                            _append_unique(orphanet_ids, orphanet_id)

                        umls_id = extract_id_from_uri(exact_match_uri, "/id/C")
                        if umls_id is not None and umls_id.isdigit():
                            _append_unique(umls_ids, "C" + umls_id)

                current_class_depth += trimmed.count("<owl:Class")
                current_class_depth -= trimmed.count("</owl:Class>")
                if current_class_depth <= 0:
                    finalize_mondo_term(
                        mappings,
                        current_mondo_id,
                        omim_ids,
                        orphanet_ids,
                        umls_ids,
                        current_is_deprecated,
                    )
                    current_mondo_id = None
                    current_is_deprecated = False
                    current_class_depth = 0
                    omim_ids = []
                    orphanet_ids = []
                    umls_ids = []
                continue

            if not trimmed.startswith('<owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_'):
                continue

            current_mondo_id = extract_mondo_id_from_uri_line(trimmed)
            current_is_deprecated = False
            current_class_depth = 1

    return mappings


def load_disease_mappings_from_obo(mondo_obo_path: str | Path) -> DiseaseMappings:
    mappings = DiseaseMappings()
    current_mondo_id: str | None = None
    current_is_deprecated = False
    omim_ids: list[str] = []
    orphanet_ids: list[str] = []
    umls_ids: list[str] = []

    def flush_term() -> None:
        nonlocal current_mondo_id, current_is_deprecated, omim_ids, orphanet_ids, umls_ids
        finalize_mondo_term(
            mappings,
            current_mondo_id,
            omim_ids,
            orphanet_ids,
            umls_ids,
            current_is_deprecated,
        )
        current_mondo_id = None
        current_is_deprecated = False
        omim_ids = []
        orphanet_ids = []
        umls_ids = []

    with open_text_reader(mondo_obo_path) as reader:
        for raw_line in reader:
            line = raw_line.strip()
            if line == "[Term]":
                flush_term()
                continue
            if line.startswith("[") and line.endswith("]"):
                flush_term()
                continue

            if line.startswith("id: MONDO:"):
                mondo_id = line.removeprefix("id: MONDO:")
                current_mondo_id = mondo_id if mondo_id.isdigit() else None
                continue

            if current_mondo_id is None:
                continue

            if line == "is_obsolete: true":
                current_is_deprecated = True
                continue

            if not line.startswith("xref: ") or 'source="MONDO:equivalentTo"' not in line:
                continue

            match = re.match(r"^xref: OMIM:(\d+)\b", line)
            if match:
                _append_unique(omim_ids, match.group(1))
                continue

            match = re.match(r"^xref: Orphanet:(\d+)\b", line)
            if match:
                _append_unique(orphanet_ids, match.group(1))
                continue

            match = re.match(r"^xref: UMLS:(C\d+)\b", line)
            if match:
                _append_unique(umls_ids, match.group(1))

    flush_term()
    return mappings


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


def extract_id_from_uri(uri: str, marker: str) -> str | None:
    start = uri.find(marker)
    if start < 0:
        return None

    start += len(marker)
    end = start
    while end < len(uri) and uri[end].isdigit():
        end += 1
    return uri[start:end] if end > start else None


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
