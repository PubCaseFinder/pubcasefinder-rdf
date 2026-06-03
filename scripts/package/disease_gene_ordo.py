from __future__ import annotations

import gc
from pathlib import Path

from rdflib import URIRef

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_gene_association_util import (
    GENCC_SOURCE_URI,
    # NCBI_GENE_INFO_PATH,
    ORDO,
    # ORPHANET_PRODUCT6_PATH,
    # RDF_DIR,
    load_gencc_definitive_associations,
    load_orphanet_gene_associations,
    merge_association_maps,
    write_gene_association_ttl,
)

logger = get_logger()

def disease_gene_ordo() -> None:
    logger.info("start Orphanet gene association RDF build")
    config = load_config('config.ini')
    orphanet_ncbi_gene_map = None
    gencc_associations = None

    # TODO:
    try:
        orphanet_ncbi_gene_map = load_orphanet_gene_associations(
            config['ncbi_gene_info_path'],
            config['orphanet_product6_path'],
        )
        logger.info("Orphanet gene association count: %s", len(orphanet_ncbi_gene_map))

        gencc_associations = load_gencc_definitive_associations(
            config['ncbi_gene_info_path'],
            config['mondo_owl_path'],
            config['gencc_submissions_path'],
        )
        before_merge = len(orphanet_ncbi_gene_map)
        merge_association_maps(orphanet_ncbi_gene_map, gencc_associations.orphanet_associations)
        logger.info("GenCC Orphanet associations added: %s", len(orphanet_ncbi_gene_map) - before_merge)
        gencc_associations = None
        gc.collect()

        source_uri_map = {
            "Orphanet": URIRef("http://www.orphadata.org/data/xml/en_product6.xml"),
            "GenCC": URIRef(GENCC_SOURCE_URI),
        }
        output_path = Path(config['rdf_output_dir']) / "Orphanet_Gene_Association.ttl"
        write_gene_association_ttl(
            output_path=output_path,
            associations=orphanet_ncbi_gene_map,
            disease_context_prefix="ORDO",
            disease_namespace_prefix="ordo",
            disease_namespace=ORDO,
            disease_id_prefix="Orphanet_",
            source_uri_map=source_uri_map,
        )
        logger.info("finished Orphanet gene association RDF build: output=%s associations=%s", output_path, len(orphanet_ncbi_gene_map))
    finally:
        gencc_associations = None
        if orphanet_ncbi_gene_map is not None:
            orphanet_ncbi_gene_map.clear()
        gc.collect()


if __name__ == "__main__":
    disease_gene_ordo()
