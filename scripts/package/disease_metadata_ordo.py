from __future__ import annotations

from pathlib import Path

from package.rdf_build_support import (
    load_config
)
from package.disease_metadata_util import load_shared_reference_data, write_orphanet_disease_ttl


def disease_metadata_ordo() -> None:
    config = load_config('config.ini')
    print(f"finish load config")
    reference_data = load_shared_reference_data(
        config['medgen_omim_hpo_path'],
        config['mondo_owl_path'],
        config['kegg_disease_path'],
        config['genereviews_omim_path']
    )
    print(f"OMIM inheritance Count : {len(reference_data.inheritance_map)}")
    print(f"Orphanet Count : {len(reference_data.mappings.orphanet_ids)}")
    print(f"OMIM KEGG Count : {len(reference_data.kegg_map)}")
    print(f"OMIM Gene_Review Count : {len(reference_data.gene_reviews_map)}")

    output_path = Path(config['rdf_output_dir']) / "Orphanet.ttl"
    write_orphanet_disease_ttl(
        output_path,
        reference_data.mappings,
        reference_data.inheritance_map,
        reference_data.kegg_map,
        reference_data.gene_reviews_map,
    )
    print(f"Orphanet All Count : {len(reference_data.mappings.orphanet_ids)}")


if __name__ == "__main__":
    disease_metadata_ordo()
