from __future__ import annotations

import gc
from pathlib import Path

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_phenotype_association_util import (
    HPOA_SOURCE_URI,
    create_annotation_source,
    load_manual_phenotype_associations,
    write_manual_phenotype_association_ttl,
)

logger = get_logger()


def disease_phenotype_omim() -> None:
    logger.info("start OMIM phenotype association RDF build")
    config = load_config('config.ini')
    omim_manual = None

    try:
        omim_manual = load_manual_phenotype_associations(config['hpo_phenotype_path'], "OMIM")
        logger.info("OMIM manual phenotype association count: %s", len(omim_manual))

        source = create_annotation_source(
            "Human Phenotype Ontology Consortium",
            HPOA_SOURCE_URI,
        )

        output_path = Path(config['rdf_output_dir']) / "OMIM_HP_Association.ttl"
        write_manual_phenotype_association_ttl(
            output_path,
            "OMIM",
            "mim",
            "https://omim.org/entry/",
            omim_manual,
            source,
        )
        logger.info("finished OMIM phenotype association RDF build: output=%s associations=%s", output_path, len(omim_manual))
    finally:
        if omim_manual is not None:
            omim_manual.clear()
        gc.collect()


if __name__ == "__main__":
    disease_phenotype_omim()
