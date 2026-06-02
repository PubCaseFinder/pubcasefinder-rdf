from __future__ import annotations

from pathlib import Path

from package.rdf_build_support import (
    load_config
)
from package.disease_phenotype_association_util import (
    HPOA_SOURCE_URI,
    create_annotation_source,
    load_manual_phenotype_associations,
    write_manual_phenotype_association_ttl,
)


def main() -> None:
    config = load_config('config.ini')
    omim_manual = load_manual_phenotype_associations(config['hpo_phenotype_path'], "OMIM")
    print(f"OMIM_HPO_Manual Count : {len(omim_manual)}")

    source = create_annotation_source(
        "Human Phenotype Ontology Consortium",
        HPOA_SOURCE_URI,
    )

    write_manual_phenotype_association_ttl(
        Path(config['rdf_output_dir']) / "OMIM_HP_Association.ttl",
        "OMIM",
        "mim",
        "https://omim.org/entry/",
        omim_manual,
        source,
    )
    print(f"OMIM manual Count : {len(omim_manual)}")


if __name__ == "__main__":
    main()
