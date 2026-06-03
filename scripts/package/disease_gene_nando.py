from __future__ import annotations

from pathlib import Path

from rdflib import URIRef

from utils.log_util import get_logger
from package.rdf_build_support import (
    load_config
)
from package.disease_gene_association_util import (
    NANDO_DISEASE,
    merge_associations_from_tsv,
    write_gene_association_ttl,
)

logger = get_logger()

def disease_gene_nando() -> None:
    config = load_config('config.ini')
    nando_ncbi_gene_map: dict[str, list[str]] = {}

    panel_search_stats = merge_associations_from_tsv(
        config['panelsearch_association_path'],
        nando_ncbi_gene_map,
        'NANDO',
        'GeneID',
        "PanelSearch",
    )
    print(f"NANDO_NCBIGene PanelSearch Count : {panel_search_stats.added}")

    nanbyou_stats = merge_associations_from_tsv(
        config['panelsearch_manual_path'],
        nando_ncbi_gene_map,
        'NANDO',
        'NCBI',
        "Nanbyou"
    )
    print(f"NANDO_NCBIGene Nanbyou Count : {nanbyou_stats.added}")
    print(f"NANDO_NCBIGene Overlap : {nanbyou_stats.overlap}")

    source_uri_map = {
        "PanelSearch": URIRef(
            "https://jshg.jp/wp-content/uploads/2024/03/a02edeee573e7797da6a821a5bc48026.pdf"
        ),
        "Nanbyou": URIRef("https://www.nanbyou.or.jp/"),
    }
    write_gene_association_ttl(
        output_path=Path(config['rdf_output_dir']) / "NANDO_Gene_Association.ttl",
        associations=nando_ncbi_gene_map,
        disease_context_prefix="NANDO",
        disease_namespace_prefix="nando",
        disease_namespace=NANDO_DISEASE,
        disease_id_prefix="",
        source_uri_map=source_uri_map,
    )


if __name__ == "__main__":
    disease_gene_nando()
