from __future__ import annotations

from pathlib import Path

from disease_phenotype_association_util import (
    HPOA_SOURCE_URI,
    HPO_PHENOTYPE_PATH,
    ORPHANET_PRODUCT4_PATH,
    RDF_DIR,
    create_annotation_source,
    load_manual_phenotype_associations,
    load_ordo_frequency_annotations,
    write_ordo_phenotype_association_ttl,
)


def main() -> None:
    orphanet_frequency = load_ordo_frequency_annotations(ORPHANET_PRODUCT4_PATH)
    print(f"Orphanet_frequency Count : {len(orphanet_frequency)}")

    orphanet_manual = load_manual_phenotype_associations(HPO_PHENOTYPE_PATH, "ORPHA")
    print(f"Orphanet_HPO_Manual Count : {len(orphanet_manual)}")

    source = create_annotation_source("Orphanet", HPOA_SOURCE_URI)

    write_ordo_phenotype_association_ttl(
        Path(RDF_DIR) / "Orphanet_HP_Association.ttl",
        orphanet_manual,
        orphanet_frequency,
        source,
    )
    print(f"Orphanet_HPO_Association Count : {len(orphanet_manual)}")


if __name__ == "__main__":
    main()
