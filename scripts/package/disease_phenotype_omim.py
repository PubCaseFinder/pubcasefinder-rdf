from __future__ import annotations

from pathlib import Path

from scripts.package.disease_phenotype_association_util import (
    HPOA_SOURCE_URI,
    HPO_PHENOTYPE_PATH,
    RDF_DIR,
    create_annotation_source,
    load_manual_phenotype_associations,
    write_manual_phenotype_association_ttl,
)


def main() -> None:
    omim_manual = load_manual_phenotype_associations(HPO_PHENOTYPE_PATH, "OMIM")
    print(f"OMIM_HPO_Manual Count : {len(omim_manual)}")

    source = create_annotation_source(
        "Human Phenotype Ontology Consortium",
        HPOA_SOURCE_URI,
    )

    write_manual_phenotype_association_ttl(
        Path(RDF_DIR) / "OMIM_HP_Association.ttl",
        "OMIM",
        "mim:",
        "PREFIX mim: <https://omim.org/entry/>",
        omim_manual,
        source,
    )
    print(f"OMIM manual Count : {len(omim_manual)}")


if __name__ == "__main__":
    main()
