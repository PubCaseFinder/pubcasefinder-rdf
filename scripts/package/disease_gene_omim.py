from __future__ import annotations

from pathlib import Path

from rdflib import URIRef

from utils.log_util import get_logger
from package.rdf_build_support import load_config
from package.disease_gene_association_util import (
    GENCC_SOURCE_URI,
    MIM,
    load_gencc_definitive_associations,
    load_omim_gene_associations,
    merge_association_maps,
    write_gene_association_ttl,
)

logger = get_logger()


def disease_gene_omim() -> None:
    config = load_config("config.ini")

    omim_ncbi_gene_map = load_omim_gene_associations(config["medgen_mim2gene_path"])
    print(f"OMIM_NCBIGene All Count : {len(omim_ncbi_gene_map)}")

    gencc_associations = load_gencc_definitive_associations(
        config["ncbigene_file_path"],
        config["mondo_owl_path"],
        config["gencc_submissions_path"],
    )
    before_merge = len(omim_ncbi_gene_map)
    merge_association_maps(omim_ncbi_gene_map, gencc_associations.omim_associations)
    print(f"GenCC_ncbigene_omim Count : {len(omim_ncbi_gene_map) - before_merge}")

    source_uri_map = {
        "MedGen": URIRef("ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen"),
        "GenCC": URIRef(GENCC_SOURCE_URI),
    }
    write_gene_association_ttl(
        output_path=Path(config["rdf_output_dir"]) / "OMIM_Gene_Association.ttl",
        associations=omim_ncbi_gene_map,
        disease_context_prefix="OMIM",
        disease_namespace_prefix="mim",
        disease_namespace=MIM,
        disease_id_prefix="",
        source_uri_map=source_uri_map,
    )


if __name__ == "__main__":
    disease_gene_omim()
