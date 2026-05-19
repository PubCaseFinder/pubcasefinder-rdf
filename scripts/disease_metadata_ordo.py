from __future__ import annotations

from pathlib import Path

from disease_metadata_util import RDF_DIR, load_shared_reference_data, write_orphanet_disease_ttl


def main() -> None:
    reference_data = load_shared_reference_data()
    print(f"OMIM inheritance Count : {len(reference_data.inheritance_map)}")
    print(f"Orphanet Count : {len(reference_data.mappings.orphanet_ids)}")
    print(f"OMIM KEGG Count : {len(reference_data.kegg_map)}")
    print(f"OMIM Gene_Review Count : {len(reference_data.gene_reviews_map)}")

    output_path = Path(RDF_DIR) / "Orphanet.ttl"
    write_orphanet_disease_ttl(
        output_path,
        reference_data.mappings,
        reference_data.inheritance_map,
        reference_data.kegg_map,
        reference_data.gene_reviews_map,
    )
    print(f"Orphanet All Count : {len(reference_data.mappings.orphanet_ids)}")


if __name__ == "__main__":
    main()
