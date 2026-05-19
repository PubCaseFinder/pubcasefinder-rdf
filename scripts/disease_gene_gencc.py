from __future__ import annotations

from pathlib import Path

from disease_gene_association_util import (
    RDF_DIR,
    load_gencc_submission_records,
    write_gencc_gene_association_ttl,
)


def main() -> None:
    records = load_gencc_submission_records()
    print(f"GenCC submission count : {len(records)}")

    write_gencc_gene_association_ttl(
        Path(RDF_DIR) / "GenCC_Gene_Association.ttl",
        records,
    )


if __name__ == "__main__":
    main()
