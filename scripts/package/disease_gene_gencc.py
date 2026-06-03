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
    config = load_config('config.ini')
    records = None

    try:
        records = load_gencc_submission_records(config['gencc_submissions_path'], config['ncbi_gene_info_path'])
        print(f"GenCC submission count : {len(records)}")

        write_gencc_gene_association_ttl(
            Path(config['rdf_output_dir']) / "GenCC_Gene_Association.ttl",
            records,
        )
    finally:
        if records is not None:
            records.clear()
        gc.collect()


if __name__ == "__main__":
    disease_gene_gencc()
