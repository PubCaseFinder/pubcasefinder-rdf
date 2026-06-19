from __future__ import annotations

import gc
from pathlib import Path

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_gene_association_util import (
    load_gencc_submission_records,
    write_gencc_gene_association_ttl,
)

logger = get_logger()

def disease_gene_gencc() -> None:
    logger.info("start GenCC gene association RDF build")
    config = load_config('config.ini')
    records = None

    try:
        records = load_gencc_submission_records(config['gencc_submissions_path'], config['ncbi_gene_info_path'])
        logger.info("GenCC submission count: %s", len(records))

        output_path = Path(config['rdf_output_dir']) / "GenCC_Gene_Association.ttl"
        write_gencc_gene_association_ttl(
            output_path,
            records,
        )
        logger.info("finished GenCC gene association RDF build: output=%s records=%s", output_path, len(records))
    finally:
        if records is not None:
            records.clear()
        gc.collect()


if __name__ == "__main__":
    disease_gene_gencc()
