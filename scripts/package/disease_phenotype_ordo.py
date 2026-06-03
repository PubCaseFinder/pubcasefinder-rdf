from __future__ import annotations

import gc
from pathlib import Path

from package.rdf_build_support import (
    load_config
)
from package.disease_phenotype_association_util import (
    HPOA_SOURCE_URI,
    create_annotation_source,
    load_manual_phenotype_associations,
    load_ordo_frequency_annotations,
    write_ordo_phenotype_association_ttl,
)


def disease_phenotype_ordo() -> None:
    config = load_config('config.ini')
    orphanet_frequency = None
    orphanet_manual = None

    try:
        orphanet_frequency = load_ordo_frequency_annotations(config['orphanet_product4_path'])
        print(f"Orphanet_frequency Count : {len(orphanet_frequency)}")

        orphanet_manual = load_manual_phenotype_associations(config['hpo_phenotype_path'], "ORPHA")
        print(f"Orphanet_HPO_Manual Count : {len(orphanet_manual)}")

        source = create_annotation_source("Orphanet", HPOA_SOURCE_URI)

        write_ordo_phenotype_association_ttl(
            Path(config['rdf_output_dir']) / "Orphanet_HP_Association.ttl",
            orphanet_manual,
            orphanet_frequency,
            source,
        )
        print(f"Orphanet_HPO_Association Count : {len(orphanet_manual)}")
    finally:
        if orphanet_manual is not None:
            orphanet_manual.clear()
        if orphanet_frequency is not None:
            orphanet_frequency.clear()
        gc.collect()


if __name__ == "__main__":
    disease_phenotype_ordo()
