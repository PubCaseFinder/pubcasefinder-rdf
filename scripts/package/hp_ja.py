from __future__ import annotations

from pathlib import Path
import re
import sys

from scripts.package.rdf_build_support import (
    load_config,
    open_text_reader,
    open_text_writer,
    resolve_configured_file,
    resolve_configured_output_dir,
    resolve_resource_root,
)


CONFIG = load_config()

HPO_INHERITANCE_JA_PATH = resolve_configured_file(
    CONFIG,
    "hpo.inheritance.ja.path",
    resolve_resource_root(CONFIG, "hpo.dir"),
    "HPO_Inheritance_en_jp.txt",
)
HPO_JAPANESE_LABEL_PATH = resolve_configured_file(
    CONFIG,
    "hpo.japanese.path",
    resolve_resource_root(CONFIG, "hpo.dir"),
    "HPO-japanese.alpha.21Jul2023.tsv",
    alternate_file_names=("HPO_id_ja.txt",),
)
RDF_DIR = resolve_configured_output_dir(CONFIG)
OUTPUT_PATH = Path(RDF_DIR) / "HPO_ja.ttl"

PREFIX_OBO = "PREFIX obo: <http://purl.obolibrary.org/obo/>"
PREFIX_RDFS = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    inheritance_file = Path(args[0]) if len(args) > 0 else Path(HPO_INHERITANCE_JA_PATH)
    japanese_file = Path(args[1]) if len(args) > 1 else Path(HPO_JAPANESE_LABEL_PATH)
    output_file = Path(args[2]) if len(args) > 2 else OUTPUT_PATH

    validate_input_file(inheritance_file)
    validate_input_file(japanese_file)

    labels: dict[str, str] = {}
    inheritance_count = load_inheritance_labels(inheritance_file, labels)
    official_count = load_official_japanese_labels(japanese_file, labels)
    write_turtle(output_file, labels)

    print(f"Inheritance labels loaded: {inheritance_count}")
    print(f"Official labels loaded: {official_count}")
    print(f"Unique labels written: {len(labels)}")
    print(f"Output: {output_file.resolve()}")


def validate_input_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path.resolve()}")


def load_inheritance_labels(path: str | Path, labels: dict[str, str]) -> int:
    count = 0
    with open_text_reader(path) as reader:
        reader.readline()
        for line in reader:
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 3:
                continue

            hpo_id = normalize_hpo_id(columns[0])
            label = columns[2].strip()
            if not hpo_id or not label:
                continue

            labels[hpo_id] = label
            count += 1
    return count


def load_official_japanese_labels(path: str | Path, labels: dict[str, str]) -> int:
    with open_text_reader(path) as reader:
        first_line = reader.readline()
        if is_legacy_hpo_label_line(first_line):
            count = load_legacy_japanese_label_line(first_line, labels)
            for line in reader:
                count += load_legacy_japanese_label_line(line, labels)
            return count

        count = 0
        for line in reader:
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 14:
                continue

            status = columns[13].strip()
            if status != "OFFICIAL":
                continue

            hpo_id = normalize_hpo_id(columns[4])
            label = columns[7].strip()
            if not hpo_id or not label or label.upper() == "NA":
                continue

            labels.setdefault(hpo_id, label)
            count += 1
    return count


def is_legacy_hpo_label_line(line: str) -> bool:
    columns = line.rstrip("\n").split("\t")
    return len(columns) >= 2 and columns[0].startswith("HP:")


def load_legacy_japanese_label_line(line: str, labels: dict[str, str]) -> int:
    columns = line.rstrip("\n").split("\t")
    if len(columns) < 2:
        return 0

    hpo_id = normalize_hpo_id(columns[0])
    label = columns[1].strip()
    if not hpo_id or not label or label.upper() == "NA":
        return 0

    labels.setdefault(hpo_id, label)
    return 1


def write_turtle(output_path: str | Path, labels: dict[str, str]) -> None:
    with open_text_writer(output_path) as writer:
        writer.write(f"{PREFIX_OBO}\n")
        writer.write(f"{PREFIX_RDFS}\n")

        for hpo_id, label in labels.items():
            writer.write(f'obo:HP_{hpo_id} rdfs:label "{escape_turtle(label)}"@ja .\n')


def normalize_hpo_id(raw_value: str) -> str:
    return re.sub(r"[^0-9]", "", raw_value)


def escape_turtle(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    main()
