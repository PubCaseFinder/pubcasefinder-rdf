import configparser
import gzip
from pathlib import Path
import sys

import pytest
from package import rdf_build_support

def create_config_files(config_content):
    parser = configparser.ConfigParser()
    parser.read_string(config_content)

    for key, value in parser["DEFAULT"].items():
        value = value.strip()
        if (
            not value
            or key.endswith("_dir")
            or key == "rdf_output_dir"
            or value.endswith(("/", "\\"))
        ):
            continue

        file_path = Path(value)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()


def test_dotted_to_snake():
    assert rdf_build_support.dotted_to_snake("ncbigene.file.path") == "ncbigene_file_path"
    assert rdf_build_support.dotted_to_snake("rdf_output_dir") == "rdf_output_dir"


def test_load_config(tmp_path):
    source_root = (tmp_path / "data" / "source").as_posix()
    rdf_output_dir = (tmp_path / "data" / "rdf" / "latest").as_posix()
    config_path = tmp_path / "config.ini"
    config_content = f"""
    [Override]
    ncbi_gene_info_path={source_root}/NCBIGene/latest/Homo_sapiens.gene_info.gz
    ncbi_gene_summary_path={source_root}/NCBIGene/latest/gene_summary.tsv.gz
    ncbi_gene_datasets_path=./tools/ncbi/datasets.exe
    ncbi_gene_dataformat_path=./tools/ncbi/dataformat.exe
    ncbi_homosapience_gene_data_uri=https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz
    omim_mim2gene_data_uri={source_root}/OMIM/latest/mim2gene.txt
    medgen_mim2gene_path={source_root}/MedGen/latest/mim2gene_medgen.txt
    medgen_omim_hpo_path={source_root}/MedGen/latest/MedGen_HPO_OMIM_Mapping.txt.gz
    orphanet_product4_path={source_root}/Orphanet/latest/en_product4.xml
    orphanet_product6_path={source_root}/Orphanet/latest/en_product6.xml
    mondo_owl_path={source_root}/MONDO/latest/mondo-international.owl
    gencc_submissions_path={source_root}/GenCC/latest/gencc-submissions.tsv
    panelsearch_association_path={source_root}/PanelSearch/latest/nando_gene_association.txt
    panelsearch_manual_path={source_root}/PanelSearch/latest/shitei_gene_all_250819.txt
    hpo_phenotype_path={source_root}/HPO/latest/phenotype.hpoa
    hpo_inheritance_ja_path={source_root}/HPO/latest/HPO_Inheritance_en_jp.txt
    hpo_japanese_path={source_root}/HPO/latest/HPO-japanese.alpha.21Jul2023.tsv
    kegg_disease_path={source_root}/KEGG/latest/KEGG_disease.tsv
    genereviews_omim_path={source_root}/GeneReviews/latest/NBKid_shortname_OMIM.txt

    rdf_output_dir={rdf_output_dir}
    """

    create_config_files(config_content)
    config_path.write_text(config_content)

    config = rdf_build_support.load_config(config_path)

    assert config['ncbigene_file_path'] == source_root + '/NCBIGene/latest/Homo_sapiens.gene_info'
    assert config['ncbigene_dir'] == source_root + '/NCBIGene/latest'


def test_open_text_writer(tmp_path):
    text_path = tmp_path / "nested" / "output.ttl"
    with rdf_build_support.open_text_writer(text_path) as writer:
        writer.write("line 1\n")
        writer.write("line 2\n")

    assert text_path.read_text(encoding="utf-8") == "line 1\nline 2\n"

    gzip_path = tmp_path / "nested" / "output.ttl.gz"
    with rdf_build_support.open_text_writer(gzip_path) as writer:
        writer.write("line 1\n")

    with gzip.open(gzip_path, "rt", encoding="utf-8") as reader:
        assert reader.read() == "line 1\n"
