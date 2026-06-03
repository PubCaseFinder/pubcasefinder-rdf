from __future__ import annotations

import argparse
import os
from collections.abc import Callable, Sequence
from pathlib import Path

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
from package import ncbi_gene_summary_helper
from package import ncbi_hgnc_gene_catalog
from package import rdf_build_support
from utils.log_util import get_logger

logger = get_logger()
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.ini"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PubCaseFinder RDF files.")

    parser.add_argument(
        "--skip-ncbi-summary",
        action="store_true",
        help="Skip NCBIGeneSummaryHelper even when the summary cache is missing.",
    )
    args = parser.parse_args(argv)
    return args


def run_step(name: str, action: Callable[[], None]) -> None:
    logger.info("=== START %s ===", name)
    try:
        action()
    except Exception:
        logger.exception("=== FAILED %s ===", name)
        raise
    logger.info("=== FINISH %s ===", name)


def should_run_ncbi_gene_summary(config: dict[str, str], args: argparse.Namespace) -> bool:
    if args.skip_ncbi_summary:
        logger.info("skip NCBIGeneSummaryHelper: --skip-ncbi-summary was specified")
        return False

    return True


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

    ncbi_gene_summary_helper.ncbi_gene_summary_helper(
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


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    os.chdir(SCRIPT_DIR)
    config = rdf_build_support.load_config(CONFIG_PATH)

    steps: list[tuple[str, Callable[[], None]]] = []
    if should_run_ncbi_gene_summary(config, args):
        steps.append(("NCBIGeneSummaryHelper", lambda: run_ncbi_gene_summary_helper(config)))

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
