
import configparser
from dataclasses import dataclass, field
import gzip
import os
import shutil
from subprocess import PIPE, Popen
import tempfile

from utils.log_util import get_logger

logger = get_logger()

@dataclass
class NCBIGeneSummaryHelperConfig(object):
    dataset_path: str
    dataformat_path: str
    output_path: str = field(default='data/NCBIGene/latest/gene_summary.tsv')

def ncbi_gene_summary_helper(config: NCBIGeneSummaryHelperConfig):
    summary_json_path = os.path.splitext(config.output_path)[0] + '.jsonl.gz'
    logger.info('start get summary process: output=%s', summary_json_path)

    ###### get ncbi dataset ########
    # https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/datasets/summary/gene/
    create_summary = None
    try:
        logger.info('starting datasets process: %s', config.dataset_path)
        create_summary = Popen([
            config.dataset_path,
            'summary',
            'gene',
            'taxon',
            'human',
            '--as-json-lines',
            '--limit',
            'all'
            ],
            stdout=PIPE,
            stderr=PIPE
        )
        logger.info('datasets process started: pid=%s', create_summary.pid)

        with gzip.open(summary_json_path, mode = 'wb') as f:
            if create_summary.stdout:
                shutil.copyfileobj(create_summary.stdout, f)

        err_create_summary = create_summary.communicate()[1]

        if create_summary.returncode != 0:
            raise RuntimeError('datasets.exe failed: ' + err_create_summary.decode())

    finally:
        if create_summary is not None and create_summary.poll() is None:
            logger.warning('killing unfinished datasets process: pid=%s', create_summary.pid)
            create_summary.kill()

    ###### format ncbi dataset ########
    # https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/dataformat/tsv/dataformat_tsv_gene/
    format_gene_summary = None
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.jsonl', delete=True, dir='.') as temp_jsonl:
        temp_jsonl_path = os.path.basename(temp_jsonl.name)

        logger.info('expanding gzip jsonl to temp file: %s', temp_jsonl_path)
        with gzip.open(summary_json_path, 'rb') as rf:
            shutil.copyfileobj(rf, temp_jsonl, length=1024 * 1024)

        format_gene_summary = Popen([
            config.dataformat_path,
            'tsv',
            'gene',
            '--inputfile',
            temp_jsonl_path,
            '--fields',
            'gene-id,summary-description',
            ],
            stdout=PIPE,
            stderr=PIPE
        )
        logger.info('dataformat process started: pid=%s', format_gene_summary.pid)

        try:
            with gzip.open(config.output_path, mode='wb') as f:
                if format_gene_summary.stdout:
                    shutil.copyfileobj(format_gene_summary.stdout, f)

            err_format = format_gene_summary.communicate()[1]

            if format_gene_summary.returncode != 0:
                raise RuntimeError('dataformat.exe failed: ' + err_format.decode())

        finally:
            if format_gene_summary is not None and format_gene_summary.poll() is None:
                logger.warning('killing unfinished dataformats process: pid=%s', format_gene_summary.pid)
                format_gene_summary.kill()

if __name__ == "__main__":
    config_ini = configparser.ConfigParser()
    config_ini.read('config.ini', encoding='utf-8')
    ncbi_gene_summary_helper_config = NCBIGeneSummaryHelperConfig(
        config_ini.get('DEFAULT', 'ncbigene_datasets_path'),
        config_ini.get('DEFAULT', 'ncbigene_dataformat_path'),
        config_ini.get('DEFAULT', 'ncbigene_summary_path')
    )
    ncbi_gene_summary_helper(ncbi_gene_summary_helper_config)