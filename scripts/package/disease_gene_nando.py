from __future__ import annotations

import gc
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
    logger.info("start NANDO gene association RDF build")
    config = load_config('config.ini')
    nando_ncbi_gene_map: dict[str, list[str]] = {}

    try:
        panel_search_stats = merge_associations_from_tsv(
            config['panelsearch_association_path'],
            nando_ncbi_gene_map,
            'NANDO',
            'GeneID',
            "PanelSearch",
        )
        logger.info("NANDO PanelSearch associations added: %s", panel_search_stats.added)

        nanbyou_stats = merge_associations_from_tsv(
            config['panelsearch_manual_path'],
            nando_ncbi_gene_map,
            'NANDO',
            'NCBI',
            "Nanbyou"
        )
        logger.info("NANDO Nanbyou associations added: %s", nanbyou_stats.added)
        logger.info("NANDO Nanbyou association overlap: %s", nanbyou_stats.overlap)

        source_uri_map = {
            "PanelSearch": URIRef(
                "https://jshg.jp/wp-content/uploads/2024/03/a02edeee573e7797da6a821a5bc48026.pdf"
            ),
            "Nanbyou": URIRef("https://www.nanbyou.or.jp/"),
        }
        output_path = Path(config['rdf_output_dir']) / "NANDO_Gene_Association.ttl"
        write_gene_association_ttl(
            output_path=output_path,
            associations=nando_ncbi_gene_map,
            disease_context_prefix="NANDO",
            disease_namespace_prefix="nando",
            disease_namespace=NANDO_DISEASE,
            disease_id_prefix="",
            source_uri_map=source_uri_map,
        )
        logger.info("finished NANDO gene association RDF build: output=%s associations=%s", output_path, len(nando_ncbi_gene_map))
    finally:
        nando_ncbi_gene_map.clear()
        gc.collect()


if __name__ == "__main__":
    disease_gene_nando()
