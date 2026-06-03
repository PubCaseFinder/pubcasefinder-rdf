from __future__ import annotations

from pathlib import Path

from package.rdf_build_support import (
    load_config
)
from package.disease_metadata_util import (
    load_omim_disease_ids,
    load_shared_reference_data,
    write_omim_disease_ttl,
)


def disease_metadata_omim() -> None:
    config = load_config('config.ini')
    omim_ids = load_omim_disease_ids(config['omim_mim2gene_data_uri'])
    print(f"OMIM All Count : {len(omim_ids)}")

    reference_data = load_shared_reference_data(
        config['medgen_omim_hpo_path'],
        config['mondo_owl_path'],
        config['kegg_disease_path'],
        config['genereviews_omim_path']
    )
    print(f"OMIM inheritance Count : {len(reference_data.inheritance_map)}")

    append_unique(omim_ids, reference_data.mappings.omim_to_mondo.keys())
    print(f"OMIM KEGG Count : {len(reference_data.kegg_map)}")
    print(f"OMIM Gene_Review Count : {len(reference_data.gene_reviews_map)}")

    write_omim_disease_ttl(
        Path(config['rdf_output_dir']) / "OMIM.ttl",
        omim_ids,
        reference_data.inheritance_map,
        reference_data.mappings,
        reference_data.kegg_map,
        reference_data.gene_reviews_map,
    )
    print(f"OMIM All Count : {len(omim_ids)}")


def append_unique(values: list[str], additions) -> None:
    seen = set(values)
    for value in additions:
        if value in seen:
            continue
        seen.add(value)
        values.append(value)


if __name__ == "__main__":
    disease_metadata_omim()
