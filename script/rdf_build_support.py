from __future__ import annotations

import configparser
import gzip
from pathlib import Path
from typing import Iterable, TextIO


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DEFAULT_RESOURCE_ROOTS = {
    "ncbigene_dir": Path("data/NCBIGene"),
    "medgen_dir": Path("data/MedGen"),
    "orphanet_dir": Path("data/Orphanet"),
    "mondo_dir": Path("data/MONDO"),
    "gencc_dir": Path("data/GenCC"),
    "panelsearch_dir": Path("data/PanelSearch"),
    "omim_dir": Path("data/OMIM"),
    "kegg_dir": Path("data/KEGG"),
    "genereviews_dir": Path("data/GeneReviews"),
    "hpo_dir": Path("data/HPO"),
}


def dotted_to_snake(key: str) -> str:
    return key.replace(".", "_")


def load_config(config_path: str | Path | None = None) -> dict[str, str]:
    path = _find_config_path(config_path)
    if path is None:
        return {}

    text = path.read_text(encoding="utf-8")
    parser = configparser.ConfigParser()

    if "[DEFAULT]" in text or any(line.strip().startswith("[") for line in text.splitlines()):
        parser.read_string(text)
        return {key: value for key, value in parser.defaults().items()}

    config: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        separator = "=" if "=" in line else ":"
        if separator not in line:
            continue
        key, value = line.split(separator, 1)
        config[key.strip()] = value.strip()
    return config


def _find_config_path(config_path: str | Path | None) -> Path | None:
    if config_path is not None:
        path = Path(config_path)
        return path if path.exists() else None

    candidates = [
        Path("config.ini"),
        REPO_ROOT / "config.ini",
        SCRIPT_DIR / "config.ini",
        Path("pcf-rdf.properties"),
        REPO_ROOT / "pcf-rdf.properties",
        SCRIPT_DIR / "pcf-rdf.properties",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def trim_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def config_value(config: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = trim_to_none(config.get(key))
        if value is not None:
            return value

        snake_key = dotted_to_snake(key)
        value = trim_to_none(config.get(snake_key))
        if value is not None:
            return value
    return None


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def resolve_configured_output_dir(config: dict[str, str]) -> str:
    configured = config_value(config, "rdf.output.dir", "rdf_output_dir")
    return normalize_path(configured) if configured is not None else "RDF/latest"


def resolve_resource_root(config: dict[str, str], directory_key: str) -> Path:
    configured = config_value(config, directory_key, dotted_to_snake(directory_key))
    if configured is not None:
        return Path(configured)

    snake_key = dotted_to_snake(directory_key)
    if snake_key not in DEFAULT_RESOURCE_ROOTS:
        raise ValueError(f"Unknown directory key: {directory_key}")
    return DEFAULT_RESOURCE_ROOTS[snake_key]


def resolve_configured_file(
    config: dict[str, str],
    exact_path_key: str,
    base_dir: Path,
    file_name: str,
    *,
    alternate_file_names: Iterable[str] = (),
    required: bool = True,
) -> str:
    configured = config_value(config, exact_path_key, dotted_to_snake(exact_path_key))
    if configured is not None:
        return normalize_path(configured)

    candidates = (file_name, *alternate_file_names)
    for candidate_name in candidates:
        resolved = resolve_latest_file(base_dir, candidate_name, required=False)
        if resolved is not None:
            return normalize_path(resolved)

        source_file = resolve_existing_path(
            Path("data/source") / candidate_name,
            REPO_ROOT / "data/source" / candidate_name,
        )
        if source_file.exists():
            return normalize_path(source_file)

    if required:
        names = ", ".join(candidates)
        raise FileNotFoundError(f"Could not find {names} under {base_dir}")
    return ""


def resolve_latest_file(base_dir: Path, file_name: str, *, required: bool = True) -> Path | None:
    base_dir = resolve_existing_path(base_dir, REPO_ROOT / base_dir)
    direct_file = base_dir / file_name
    if direct_file.exists():
        return direct_file

    latest_file = base_dir / "latest" / file_name
    if latest_file.exists():
        return latest_file

    if not base_dir.is_dir():
        if required:
            raise FileNotFoundError(f"Could not find {file_name} under {base_dir}")
        return None

    children = sorted(
        (path for path in base_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )
    for child in children:
        child_file = child / file_name
        if child_file.exists():
            return child_file

    if required:
        raise FileNotFoundError(f"Could not find {file_name} under {base_dir}")
    return None


def resolve_existing_path(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def open_text_reader(path: str | Path) -> TextIO:
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def open_text_writer(path: str | Path) -> TextIO:
    path = Path(path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        return gzip.open(path, "wt", encoding="utf-8", newline="\n")
    return path.open("wt", encoding="utf-8", newline="\n")
