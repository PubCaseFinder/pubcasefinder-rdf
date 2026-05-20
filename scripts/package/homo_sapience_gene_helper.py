# get_data.pyで補うかも

import configparser
from dataclasses import dataclass, field
from subprocess import PIPE, Popen
import urllib.request
import urllib.error

from utils.log_util import get_logger

logger = get_logger()

@dataclass
class HomoSapienceGeneHelperConfig(object):
    data_path: str
    url: str = field(default='https://ftp.ncbi.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz')

def homo_sapience_gene_helper(config: HomoSapienceGeneHelperConfig):
    try:
        urllib.request.urlretrieve(config.url, config.data_path)
    except urllib.error.ContentTooShortError as e:
        logger.error('ContentTooShortError: %s', e)


if __name__ == "__main__":
    config_ini = configparser.ConfigParser()
    config_ini.read('config.ini', encoding='utf-8')
    ncbi_homo_sapience_gene_helper_config = HomoSapienceGeneHelperConfig(
        config_ini.get('DEFAULT', 'ncbi_homosapience_gene_data_path'),
        config_ini.get('DEFAULT', 'ncbi_homosapience_gene_data_uri')
    )
    homo_sapience_gene_helper(ncbi_homo_sapience_gene_helper_config)