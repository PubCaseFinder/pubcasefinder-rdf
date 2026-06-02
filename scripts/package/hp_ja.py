from __future__ import annotations

from pathlib import Path
import re

import duckdb
import rdflib
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDFS

from package.rdf_build_support import load_config, open_text_writer

OBO = Namespace("http://purl.obolibrary.org/obo/")

def main() -> None:
    config = load_config('config.ini')

    labels, inheritance_count, official_count = load_hpo_japanese_labels(
        config["hpo_inheritance_ja_path"],
        config["hpo_japanese_path"],
    )
    output_path = Path(config["rdf_output_dir"]) / "HPO_ja.ttl"
    write_hpo_japanese_ttl(output_path, labels)

    print(f"Inheritance labels loaded: {inheritance_count}")
    print(f"Official labels loaded: {official_count}")
    print(f"Unique labels written: {len(labels)}")


def load_hpo_japanese_labels(
    inheritance_path: str | Path,
    japanese_path: str | Path,
) -> tuple[dict[str, str], int, int]:
    labels: dict[str, str] = {}
    inheritance_count = add_inheritance_labels(inheritance_path, labels)
    official_count = add_official_japanese_labels(japanese_path, labels)
    return labels, inheritance_count, official_count


def add_inheritance_labels(path: str | Path, labels: dict[str, str]) -> int:
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
    return count


def add_official_japanese_labels(path: str | Path, labels: dict[str, str]) -> int:
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
    return count


def write_hpo_japanese_ttl(output_path: str | Path, labels: dict[str, str]) -> None:
    graph = Graph()
    graph.bind('obo', OBO)
    graph.bind('rdfs', RDFS)

    for hpo_id, label in labels.items():
        graph.add((OBO[f'HP_{hpo_id}'], RDFS.label, Literal(label, lang='ja')))
    with open_text_writer(output_path) as writer:
        writer.write(graph.serialize(format='turtle'))

if __name__ == "__main__":
    main()
