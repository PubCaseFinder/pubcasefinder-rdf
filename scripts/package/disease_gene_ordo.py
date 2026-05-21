from __future__ import annotations

from pathlib import Path

from rdflib import URIRef

from scripts.package.disease_gene_association_util import (
    GENCC_SOURCE_URI,
    NCBI_GENE_INFO_PATH,
    ORDO,
    ORPHANET_PRODUCT6_PATH,
    RDF_DIR,
    load_gencc_definitive_associations,
    load_orphanet_gene_associations,
    merge_association_maps,
    write_gene_association_ttl,
)


def main() -> None:
    orphanet_ncbi_gene_map = load_orphanet_gene_associations(
        NCBI_GENE_INFO_PATH,
        ORPHANET_PRODUCT6_PATH,
    )
    print(f"Orphanet NCBI Count : {len(orphanet_ncbi_gene_map)}")

    gencc_associations = load_gencc_definitive_associations()
    before_merge = len(orphanet_ncbi_gene_map)
    merge_association_maps(orphanet_ncbi_gene_map, gencc_associations.orphanet_associations)
    print(f"GenCC_ncbigene_orpha Count : {len(orphanet_ncbi_gene_map) - before_merge}")

    source_uri_map = {
        "Orphanet": URIRef("http://www.orphadata.org/data/xml/en_product6.xml"),
        "GenCC": URIRef(GENCC_SOURCE_URI),
    }
    write_gene_association_ttl(
        output_path=Path(RDF_DIR) / "Orphanet_Gene_Association.ttl",
        associations=orphanet_ncbi_gene_map,
        disease_context_prefix="ORDO",
        disease_namespace_prefix="ordo",
        disease_namespace=ORDO,
        disease_id_prefix="Orphanet_",
        source_uri_map=source_uri_map,
    )


if __name__ == "__main__":
    main()
