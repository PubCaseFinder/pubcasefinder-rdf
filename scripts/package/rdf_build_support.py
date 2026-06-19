from __future__ import annotations

import configparser
import gzip
from pathlib import Path
from typing import TextIO
from utils.log_util import get_logger

logger = get_logger()

def dotted_to_snake(key: str) -> str:
    return key.replace(".", "_")

# config pathを与えてconfigを読み取りディクショナリで返す
def load_config(config_path: str | Path | None = None) -> dict[str, str]:
    if config_path is None:
        logger.error('Missing required config path')
        return {}
    logger.info("loading config: path=%s", config_path)
    path = Path(config_path)

    if not path.exists():
        logger.error('File is not exist: %s', path)
        return {}

    default_config = {
        'ncbi_gene_info_path': '../data/source/NCBIGene/latest/Homo_sapiens.gene_info.gz',
        'ncbi_gene_summary_path': '../data/source/NCBIGene/latest/gene_summary.tsv.gz',
        'ncbi_gene_datasets_path': '',
        'ncbi_gene_dataformat_path': '',
        'ncbi_gene_info_url': '',
        'omim_mim2gene_data_path': '../data/source/OMIM/latest/mim2gene.txt',
        'omim_mim2gene_data_url': '',
        'medgen_mim2gene_path': '../data/source/MedGen/latest/mim2gene_medgen.txt',
        'medgen_mim2gene_url': '',
        'medgen_omim_hpo_path': '../data/source/MedGen/latest/MedGen_HPO_OMIM_Mapping.txt.gz',
        'medgen_omim_hpo_url': '',
        'orphanet_product4_path': '../data/source/Orphanet/latest/en_product4.xml',
        'orphanet_product4_url': '',
        'orphanet_product6_path': '../data/source/Orphanet/latest/en_product6.xml',
        'orphanet_product6_url': '',
        'mondo_owl_path': '../data/source/MONDO/latest/mondo-international.owl',
        'mondo_owl_url': '',
        'gencc_submissions_path': '../data/source/GenCC/latest/gencc-submissions.tsv',
        'gencc_submissions_url': '',
        'panelsearch_association_path': '../data/source/PanelSearch/latest/nando_gene_association.txt',
        'panelsearch_manual_path': '../data/source/PanelSearch/latest/shitei_gene_all.txt',
        'panelsearch_manual_url': '',
        'hpo_phenotype_path': '../data/source/HPO/latest/phenotype.hpoa',
        'hpo_phenotype_url': '',
        'hpo_inheritance_ja_path': '../data/source/HPO/latest/HPO_Inheritance_en_jp.txt',
        'hpo_inheritance_url': '',
        'hpo_inheritance_path': '../data/source/HPO/latest/hp.owl',
        'hpo_japanese_path': '../data/source/HPO/latest/HPO-japanese.alpha.21Jul2023.tsv',
        'hpo_japanese_url': '',
        'kegg_disease_path': '../data/source/KEGG/latest/KEGG_disease.tsv',
        'genereviews_omim_path': '../data/source/GeneReviews/latest/NBKid_shortname_OMIM.txt',
        'genereviews_omim_url': '',
        'rdf_output_dir': '../data/rdf',
    }

    parser = configparser.ConfigParser(default_config, interpolation=None)
    parser.read(path, encoding='utf-8')
    config = dict(parser['Override'])

    logger.info("loaded config: path=%s entries=%s", path, len(config))
    return config

def open_text_writer(path: str | Path) -> TextIO:
    path = Path(path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("opening text writer: path=%s", path)
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8", newline="\n")
    return path.open("wt", encoding="utf-8", newline="\n")
