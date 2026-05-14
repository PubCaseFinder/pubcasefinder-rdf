from __future__ import annotations

from pathlib import Path

from disease_gene_association_util import (
    NANDO_ASSOCIATION_PATH,
    NANDO_MANUAL_PATH,
    RDF_DIR,
    merge_associations_from_tsv,
    write_gene_association_ttl,
)


def main() -> None:
    nando_ncbi_gene_map: dict[str, list[str]] = {}

    panel_search_stats = merge_associations_from_tsv(
        NANDO_ASSOCIATION_PATH,
        nando_ncbi_gene_map,
        1,
        3,
        "PanelSearch",
        skip_first_line=True,
    )
    print(f"NANDO_NCBIGene PanelSearch Count : {panel_search_stats.added}")

    nanbyou_stats = merge_associations_from_tsv(
        NANDO_MANUAL_PATH,
        nando_ncbi_gene_map,
        4,
        7,
        "Nanbyou",
        skip_first_line=True,
    )
    print(f"NANDO_NCBIGene Nanbyou Count : {nanbyou_stats.added}")
    print(f"NANDO_NCBIGene Overlap : {nanbyou_stats.overlap}")

    source_uri_map = {
        "PanelSearch": "https://jshg.jp/wp-content/uploads/2024/03/a02edeee573e7797da6a821a5bc48026.pdf",
        "Nanbyou": "https://www.nanbyou.or.jp/",
    }
    write_gene_association_ttl(
        Path(RDF_DIR) / "NANDO_Gene_Association.ttl",
        nando_ncbi_gene_map,
        "NANDO",
        "nando:",
        "PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>",
        source_uri_map,
    )


if __name__ == "__main__":
    main()
