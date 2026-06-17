from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from pathlib import Path
import re

from package import disease_gene_gencc
from package import disease_gene_mondo
from package import disease_gene_nando
from package import disease_gene_omim
from package import disease_gene_ordo
from package import disease_metadata_omim
from package import disease_metadata_ordo
from package import disease_phenotype_omim
from package import disease_phenotype_ordo
from package import hp_ja
from package import get_data_helper
from package import ncbi_hgnc_gene_catalog
from package import rdf_build_support
from utils.log_util import get_logger

logger = get_logger()
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.ini"

def should_run_ncbi_gene_summary(
    ncbi_gene_datasets_path,
    ncbi_gene_dataformat_path,
    ncbi_gene_summary_path,
) -> bool:
    if (ncbi_gene_datasets_path is None or ncbi_gene_datasets_path == '') or (ncbi_gene_dataformat_path is None or ncbi_gene_dataformat_path == '') or (ncbi_gene_summary_path is None or ncbi_gene_summary_path == ''):
        return False
    else:
        return True

def create_download_data_list(config: dict[str, str]) -> list[str]:
    download_data_list = []
    for key in config:
        if not key.endswith('url'):
            continue
        if config[key] is None or config[key] == '':
            continue
        key_of_path = re.sub(r'url', 'path', key)
        download_data_list.append((config[key], config[key_of_path]))
    return download_data_list


def run_step(name: str, action: Callable[[], None]) -> None:
    logger.info("=== START %s ===", name)
    try:
        action()
    except Exception:
        logger.exception("=== FAILED %s ===", name)
        raise
    logger.info("=== FINISH %s ===", name)


def run_ncbi_gene_summary_helper(config: dict[str, str]) -> None:
    required_keys = [
        "ncbi_gene_datasets_path",
        "ncbi_gene_dataformat_path",
        "ncbi_gene_summary_path",
    ]
    missing_keys = [key for key in required_keys if not config.get(key)]
    if missing_keys:
        raise KeyError(
            "Missing config key(s) for NCBIGeneSummaryHelper: "
            + ", ".join(missing_keys)
        )

    get_data_helper.ncbi_gene_summary_helper(
        config["ncbi_gene_datasets_path"],
        config["ncbi_gene_dataformat_path"],
        config["ncbi_gene_summary_path"],
    )


def run_ncbi_hgnc_gene_catalog(config: dict[str, str]) -> None:
    ncbi_hgnc_gene_catalog.ncbi_hgnc_gene_catalog(
        config["ncbi_gene_info_path"],
        config["ncbi_gene_summary_path"],
        Path(config["rdf_output_dir"]) / "all_gene.ttl",
    )


def main() -> None:
    os.chdir(SCRIPT_DIR)
    config = rdf_build_support.load_config(CONFIG_PATH)

    steps: list[tuple[str, Callable[[], None]]] = []
    if should_run_ncbi_gene_summary(config['ncbi_gene_datasets_path'], config['ncbi_gene_dataformat_path'], config['ncbi_gene_summary_path']):
        steps.append(("NCBIGeneSummaryHelper", lambda: run_ncbi_gene_summary_helper(config)))

    download_data_list = create_download_data_list(config)
    if download_data_list != []:
        get_data_helper.download_data_set(download_data_list)
    steps.extend(
        [
            ("NCBIHGNCGeneCatalog", lambda: run_ncbi_hgnc_gene_catalog(config)),
            ("DiseaseMetadataOMIM", disease_metadata_omim.disease_metadata_omim),
            ("DiseaseMetadataORDO", disease_metadata_ordo.disease_metadata_ordo),
            ("DiseasePhenotypeOMIM", disease_phenotype_omim.disease_phenotype_omim),
            ("DiseasePhenotypeORDO", disease_phenotype_ordo.disease_phenotype_ordo),
            ("DiseaseGeneOMIM", disease_gene_omim.disease_gene_omim),
            ("DiseaseGeneORDO", disease_gene_ordo.disease_gene_ordo),
            ("DiseaseGeneMONDO", disease_gene_mondo.disease_gene_mondo),
            ("DiseaseGeneNANDO", disease_gene_nando.disease_gene_nando),
            ("DiseaseGeneGenCC", disease_gene_gencc.disease_gene_gencc),
            ("HP_ja", hp_ja.hp_ja),
        ]
    )

    for name, action in steps:
        run_step(name, action)


if __name__ == "__main__":
    main()
