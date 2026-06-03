from __future__ import annotations

import gc
from pathlib import Path

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_metadata_util import load_shared_reference_data, write_orphanet_disease_ttl

logger = get_logger()


def disease_metadata_ordo() -> None:
    logger.info("start Orphanet disease metadata RDF build")
    config = load_config('config.ini')
    reference_data = None
    logger.info("finished loading config")
    try:
        reference_data = load_shared_reference_data(
            config['medgen_omim_hpo_path'],
            config['mondo_owl_path'],
            config['kegg_disease_path'],
            config['genereviews_omim_path']
        )
        logger.info("OMIM inheritance count: %s", len(reference_data.inheritance_map))
        logger.info("Orphanet disease count: %s", len(reference_data.mappings.orphanet_ids))
        logger.info("OMIM KEGG count: %s", len(reference_data.kegg_map))
        logger.info("OMIM GeneReviews count: %s", len(reference_data.gene_reviews_map))

        output_path = Path(config['rdf_output_dir']) / "Orphanet.ttl"
        write_orphanet_disease_ttl(
            output_path,
            reference_data.mappings,
            reference_data.inheritance_map,
            reference_data.kegg_map,
            reference_data.gene_reviews_map,
        )
        logger.info("finished Orphanet disease metadata RDF build: output=%s diseases=%s", output_path, len(reference_data.mappings.orphanet_ids))
    finally:
        reference_data = None
        gc.collect()


if __name__ == "__main__":
    disease_metadata_ordo()
