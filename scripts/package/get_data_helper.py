import gc
from collections.abc import Iterable
from dataclasses import dataclass
import gzip
import os
from pathlib import Path
import shutil
from subprocess import PIPE, Popen
import tempfile
import re

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS
import duckdb

from package.rdf_build_support import load_config, open_text_writer
from utils.get_data import download_file
from utils.log_util import get_logger

logger = get_logger()

OBO = Namespace("http://purl.obolibrary.org/obo/")


@dataclass
class inheritance_map:
    id: str
    en: str
    ja: str | None = None


def get_subclass(
    root_uri: URIRef,
    inheritance_map_list: list[inheritance_map],
    attach_prefix: str,
    remove_prefix: str,
    graph: Graph,
    visited: set[str] | None = None,
) -> None:
    if visited is None:
        visited = set()

    root_key = str(root_uri)
    if root_key in visited:
        return
    visited.add(root_key)

    children = sorted(graph.subjects(RDFS.subClassOf, root_uri), key=str)
    for child in children:
        if str(child) in visited:
            continue

        child_en_list = sorted(graph.objects(child, RDFS.label), key=str)
        for child_en in child_en_list:
            inheritance_map_list.append(
                inheritance_map(
                    id=attach_prefix + str(child).removeprefix(remove_prefix),
                    en=str(child_en),
                    ja='',
                )
            )
        get_subclass(child, inheritance_map_list, attach_prefix, remove_prefix, graph, visited)


def update_hpo_subclass(hpo_owl_path: str | Path, mode_of_inheritance_id: str) -> list[inheritance_map]:
    logger.info(
        "loading HPO inheritance subclass tree: path=%s root=HP:%s",
        hpo_owl_path,
        mode_of_inheritance_id,
    )
    graph = Graph()
    graph.parse(str(hpo_owl_path), format='xml')

    inheritance_map_list: list[inheritance_map] = []
    root_uri = OBO['HP_' + mode_of_inheritance_id]
    root_en_list = sorted(graph.objects(root_uri, RDFS.label), key=str)
    for root_en in root_en_list:
        inheritance_map_list.append(
            inheritance_map(
                id='HP:' + mode_of_inheritance_id,
                en=str(root_en),
                ja=None,
            )
        )

    get_subclass(
        root_uri,
        inheritance_map_list,
        'HP:',
        'http://purl.obolibrary.org/obo/HP_',
        graph,
    )
    logger.info(
        "loaded HPO inheritance subclass tree: path=%s terms=%s",
        hpo_owl_path,
        len(inheritance_map_list),
    )
    return inheritance_map_list

def create_hpo_inheritance_en_ja(inheritance_ja_path_name: str | Path, inheritance_map_list: list[inheritance_map]) -> None:
    logger.info("creating HPO inheritance Japanese mapping: path=%s", inheritance_ja_path_name)
    hpo_inheritance_en_ja_old_path = str(Path(inheritance_ja_path_name).with_suffix('')) + '_old.txt'
    hpo_inheritance_en_ja_new_path = str(Path(inheritance_ja_path_name).with_suffix('')) + '_new.txt'
    shutil.copy2(inheritance_ja_path_name, hpo_inheritance_en_ja_old_path)
    with open(hpo_inheritance_en_ja_new_path, 'w', encoding='utf-8') as writer:
        writer.write('HPO ID\t英語\t日本語\n')
        for hpo_inheritance in inheritance_map_list:
            writer.write(f'{hpo_inheritance.id}\t{hpo_inheritance.en}\t{hpo_inheritance.ja or ""}\n')

    con = duckdb.connect()
    query_statement = f"""
        copy (
            select
                n."HPO ID",
                n."英語",
                o."日本語"
            from read_csv('{hpo_inheritance_en_ja_new_path}', delim='\\t', all_varchar=true) as n
            left join read_csv('{hpo_inheritance_en_ja_old_path}', delim='\\t', all_varchar=true) as o
            on n."英語" = o."英語"
        ) to '{inheritance_ja_path_name}' (FORMAT CSV, DELIMITER '\\t', HEADER true)
        """
    _ = con.execute(query_statement)
    logger.info("created HPO inheritance Japanese mapping: path=%s count=%s", inheritance_ja_path_name, len(inheritance_map_list))


def check_hpo_inheritance_en_ja(inheritance_ja_path_name: str | Path) -> bool:
    logger.info("checking HPO inheritance Japanese mapping: path=%s", inheritance_ja_path_name)
    con = duckdb.connect()
    query_statement = f"""
        select
            "HPO ID"
        from read_csv('{inheritance_ja_path_name}', delim='\\t', all_varchar=true) as n
        where "日本語" is null or trim("日本語") = ''
        """
    res = con.execute(query_statement)
    jp_empty_id = []
    while True:
        row = res.fetchone()
        if row is None:
            break
        jp_empty_id.append(row[0])
    if len(jp_empty_id) == 0:
        logger.info("all HPO inheritance Japanese mappings are translated: path=%s", inheritance_ja_path_name)
        return True

    logger.warning('need translate english ontologies: %s', len(jp_empty_id))
    return False

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

def iter_kegg_omim_mappings(kegg_disease_path: str | Path) -> Iterable[tuple[str, str]]:
    logger.info("reading KEGG disease OMIM mappings: path=%s", kegg_disease_path)
    kegg_id = None
    current_field = None
    seen_pairs = set()

    with open(kegg_disease_path, encoding="utf-8") as reader:
        for raw_line in reader:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue

            if line.startswith("///"):
                kegg_id = None
                current_field = None
                continue

            field = line[:12].strip()
            value = line[12:].strip() if len(line) > 12 else ""

            if field:
                current_field = field
                if field == "ENTRY":
                    kegg_id = value.split()[0] if value else None
                elif current_field != "DBLINKS":
                    continue
            elif current_field == "DBLINKS":
                value = line.strip()
            else:
                continue

            if current_field != "DBLINKS" or kegg_id is None:
                continue

            match = re.match(r"OMIM:\s*(.+)", value)
            if match is None:
                continue

            for omim_id in re.findall(r"\d+", match.group(1)):
                pair = (omim_id, kegg_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                yield pair

    logger.info("read KEGG disease OMIM mappings: path=%s pairs=%s", kegg_disease_path, len(seen_pairs))


def create_kegg_disease_omim_tsv(kegg_disease_path: str | Path, output_path: str | Path) -> None:
    logger.info(
        "creating KEGG disease OMIM TSV: source=%s output=%s",
        kegg_disease_path,
        output_path,
    )
    count = 0
    with open_text_writer(output_path) as writer:
        for omim_id, kegg_id in iter_kegg_omim_mappings(kegg_disease_path):
            writer.write(f"{omim_id}\t{kegg_id}\n")
            count += 1
    logger.info("created KEGG disease OMIM TSV: output=%s pairs=%s", output_path, count)


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


    inheritance_map_list = update_hpo_subclass(config['hpo_inheritance_path'], '0000005')
    create_hpo_inheritance_en_ja(config['hpo_inheritance_ja_path'], inheritance_map_list)
    _ = check_hpo_inheritance_en_ja(config['hpo_inheritance_ja_path'])
