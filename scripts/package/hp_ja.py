from __future__ import annotations

import gc
from pathlib import Path
import re

import duckdb
import rdflib
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDFS

from utils.log_util import get_logger
from package.rdf_build_support import load_config, open_text_writer

OBO = Namespace("http://purl.obolibrary.org/obo/")

logger = get_logger()

def hp_ja() -> None:
    logger.info("start HPO Japanese label RDF build")
    config = load_config('config.ini')
    labels = None

    try:
        labels, inheritance_count, official_count = load_hpo_japanese_labels(
            config["hpo_inheritance_ja_path"],
            config["hpo_japanese_path"],
        )
        output_path = Path(config["rdf_output_dir"]) / "HPO_ja.ttl"
        write_hpo_japanese_ttl(output_path, labels)

        logger.info("inheritance labels loaded: %s", inheritance_count)
        logger.info("official labels loaded: %s", official_count)
        logger.info("finished HPO Japanese label RDF build: output=%s unique_labels=%s", output_path, len(labels))
    finally:
        if labels is not None:
            labels.clear()
        gc.collect()


def load_hpo_japanese_labels(
    inheritance_path: str | Path,
    japanese_path: str | Path,
) -> tuple[dict[str, str], int, int]:
    logger.info(
        "loading HPO Japanese labels: inheritance_path=%s japanese_path=%s",
        inheritance_path,
        japanese_path,
    )
    labels: dict[str, str] = {}
    inheritance_count = add_inheritance_labels(inheritance_path, labels)
    official_count = add_official_japanese_labels(japanese_path, labels)
    logger.info(
        "loaded HPO Japanese labels: inheritance=%s official=%s unique=%s",
        inheritance_count,
        official_count,
        len(labels),
    )
    return labels, inheritance_count, official_count


def add_inheritance_labels(path: str | Path, labels: dict[str, str]) -> int:
    logger.info("loading HPO inheritance Japanese labels: path=%s", path)
    count = 0
    con = duckdb.connect()
    query_statement = f"""
        select
            replace("HPO ID", 'HP:', ''),
            "日本語"
        from read_csv('{path}', delim='\t', all_varchar=true)
        """
    res = con.execute(query_statement)

    while True:
        row = res.fetchone()
        if row is None:
            break

        hpo_id = row[0]
        label = row[1].strip() if row[1] is not None else ""
        if not hpo_id or not label:
            continue

        labels[hpo_id] = label
        count += 1
    logger.info("loaded HPO inheritance Japanese labels: path=%s count=%s", path, count)
    return count


def add_official_japanese_labels(path: str | Path, labels: dict[str, str]) -> int:
    logger.info("loading official HPO Japanese labels: path=%s", path)
    count = 0
    con = duckdb.connect()
    query_statement = f"""
        select
            replace(subject_id, 'HP:', ''),
            translation_value
        from
            read_csv('{path}', delim='\t', all_varchar=true)
        where
            trim(translation_status) = 'OFFICIAL'
            and
            translation_value != 'NA'
    """
    res = con.execute(query_statement)

    while True:
        row = res.fetchone()
        if row is None:
            break

        hpo_id = row[0]
        label = row[1].strip() if row[1] is not None else ""

        labels.setdefault(hpo_id, label)
        count += 1
    logger.info("loaded official HPO Japanese labels: path=%s count=%s", path, count)
    return count


def write_hpo_japanese_ttl(output_path: str | Path, labels: dict[str, str]) -> None:
    logger.info("writing HPO Japanese label TTL: output=%s labels=%s", output_path, len(labels))
    graph = Graph()
    graph.bind('obo', OBO)
    graph.bind('rdfs', RDFS)

    for hpo_id, label in labels.items():
        graph.add((OBO[f'HP_{hpo_id}'], RDFS.label, Literal(label, lang='ja')))
    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format='turtle'))
    logger.info("finished writing HPO Japanese label TTL: output=%s triples=%s", output_path, len(graph))

if __name__ == "__main__":
    hp_ja()
