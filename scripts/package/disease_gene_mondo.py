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
    OBO,
    build_mondo_gene_associations,
    write_gene_association_ttl,
)

logger = get_logger()

def disease_gene_mondo() -> None:
    logger.info("start MONDO gene association RDF build")
    config = load_config('config.ini')
    mondo_ncbi_gene_map = None

    try:
        mondo_ncbi_gene_map = build_mondo_gene_associations(
            config['ncbi_gene_info_path'],
            config['mondo_owl_path'],
            config['gencc_submissions_path'],
            config['medgen_mim2gene_path'],
            config['orphanet_product6_path']
        )
        logger.info("MONDO gene association count: %s", len(mondo_ncbi_gene_map))

        source_uri_map = {
            "MedGen": URIRef("ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen"),
            "Orphanet": URIRef("http://www.orphadata.org/data/xml/en_product6.xml"),
            "GenCC": URIRef(GENCC_SOURCE_URI),
        }
        output_path = Path(config['rdf_output_dir']) / "MONDO_Gene_Association.ttl"
        write_gene_association_ttl(
            output_path=output_path,
            associations=mondo_ncbi_gene_map,
            disease_context_prefix="MONDO",
            disease_namespace_prefix="obo",
            disease_namespace=OBO,
            disease_id_prefix="MONDO_",
            source_uri_map=source_uri_map,
        )
        logger.info("finished MONDO gene association RDF build: output=%s associations=%s", output_path, len(mondo_ncbi_gene_map))
    finally:
        if mondo_ncbi_gene_map is not None:
            mondo_ncbi_gene_map.clear()
        gc.collect()


if __name__ == "__main__":
    disease_gene_mondo()
