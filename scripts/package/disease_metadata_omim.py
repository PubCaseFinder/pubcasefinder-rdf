from __future__ import annotations

import gc
from pathlib import Path

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_metadata_util import (
    load_omim_disease_ids,
    load_shared_reference_data,
    write_omim_disease_ttl,
)

logger = get_logger()


def disease_metadata_omim() -> None:
    logger.info("start OMIM disease metadata RDF build")
    config = load_config('config.ini')
    omim_ids = None
    reference_data = None

    try:
        omim_ids = load_omim_disease_ids(config['omim_mim2gene_data_path'])
        logger.info("OMIM disease count: %s", len(omim_ids))

        reference_data = load_shared_reference_data(
            config['medgen_omim_hpo_path'],
            config['mondo_owl_path'],
            config['kegg_disease_path'],
            config['genereviews_omim_path']
        )
        logger.info("OMIM inheritance count: %s", len(reference_data.inheritance_map))

        append_unique(omim_ids, reference_data.mappings.omim_to_mondo.keys())
        logger.info("OMIM KEGG count: %s", len(reference_data.kegg_map))
        logger.info("OMIM GeneReviews count: %s", len(reference_data.gene_reviews_map))

        output_path = Path(config['rdf_output_dir']) / "OMIM.ttl"
        write_omim_disease_ttl(
            output_path,
            omim_ids,
            reference_data.inheritance_map,
            reference_data.mappings,
            reference_data.kegg_map,
            reference_data.gene_reviews_map,
        )
        logger.info("finished OMIM disease metadata RDF build: output=%s diseases=%s", output_path, len(omim_ids))
    finally:
        reference_data = None
        if omim_ids is not None:
            omim_ids.clear()
        gc.collect()


def append_unique(values: list[str], additions) -> None:
    before_count = len(values)
    seen = set(values)
    for value in additions:
        if value in seen:
            continue
        seen.add(value)
        values.append(value)
    logger.info("appended unique values: before=%s after=%s added=%s", before_count, len(values), len(values) - before_count)


if __name__ == "__main__":
    disease_metadata_omim()
