import gc
from dataclasses import dataclass, field
import gzip
import os
import shutil
from subprocess import PIPE, Popen
import tempfile
import re

from package.rdf_build_support import load_config
from utils.get_data import download_file
from utils.log_util import get_logger

logger = get_logger()
def ncbi_gene_summary_helper(
        ncbi_gene_datasets_path: str,
        ncbi_gene_dataformat_path: str,
        ncbi_gene_summary_path: str
) -> None:
    summary_json_path = os.path.splitext(ncbi_gene_summary_path)[0] + '.jsonl.gz'
    logger.info('start get summary process: output=%s', summary_json_path)

    ###### get ncbi dataset ########
    # https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/command-line/datasets/summary/gene/
    create_summary = None
    try:
        logger.info('starting datasets process: %s', ncbi_gene_datasets_path)
        create_summary = Popen([
            ncbi_gene_datasets_path,
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
            raise RuntimeError('datasets failed: ' + err_create_summary.decode())

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
            temp_jsonl.flush()

        format_gene_summary = Popen([
            ncbi_gene_dataformat_path,
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
            with gzip.open(ncbi_gene_summary_path, mode='wb') as f:
                if format_gene_summary.stdout:
                    shutil.copyfileobj(format_gene_summary.stdout, f)

            err_format = format_gene_summary.communicate()[1]

            if format_gene_summary.returncode != 0:
                raise RuntimeError('dataformat.exe failed: ' + err_format.decode())

        finally:
            if format_gene_summary is not None and format_gene_summary.poll() is None:
                logger.warning('killing unfinished dataformats process: pid=%s', format_gene_summary.pid)
                format_gene_summary.kill()
    logger.info('finished get summary process: output=%s', ncbi_gene_summary_path)
    gc.collect()

# 引数: データのURI, データの出力path
def download_data_set(data_list: list[set[str]]) -> None:
    for data_uri, data_path in data_list:
        try:
            _ = download_file(
                data_uri,
                data_path,
            )
        finally:
            gc.collect()

if __name__ == "__main__":
    config = load_config('config.ini')
    if all([
        config['ncbi_gene_datasets_path'],
        config['ncbi_gene_dataformat_path'],
        config['ncbi_gene_summary_path'],

    ]):
        ncbi_gene_summary_helper(
            config['ncbi_gene_datasets_path'],
            config['ncbi_gene_dataformat_path'],
            config['ncbi_gene_summary_path'],
        )

    download_data_list = []
    for key in config:
        if not key.endswith('url'):
            continue
        if config[key] is None or config[key] == '':
            continue
        key_of_path = re.sub(r'url', 'path', key)
        download_data_list.append((config[key], config[key_of_path]))
    download_data_set(download_data_list)