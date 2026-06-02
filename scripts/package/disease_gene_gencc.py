from __future__ import annotations

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

def main() -> None:
    # TODO: 変数化したい
    config = load_config('config.ini')
    records = load_gencc_submission_records(config['gencc_submissions_path'], config['ncbigene_file_path'])
    print(f"GenCC submission count : {len(records)}")

    write_gencc_gene_association_ttl(
        Path(config['rdf_output_dir']) / "GenCC_Gene_Association.ttl",
        records,
    )


if __name__ == "__main__":
    main()
