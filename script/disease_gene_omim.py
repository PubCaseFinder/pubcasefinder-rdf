from dataclasses import dataclass, field
from pathlib import Path
import configparser
import csv
import re

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, SKOS

from uils.get_data import GetDataConfig, get_data


@dataclass
class OMIMGetDataConfig(GetDataConfig):
    output_dir: str = field(default_factory='data/OMIM')

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

MONDO = Namespace("http://purl.obolibrary.org/obo/MONDO_")
OMIM_URI_PATTERN = re.compile(r"(?:/omim/|omim\.org/entry/)(\d+)")


def mondo_id(mondo_uri: URIRef) -> str | None:
    uri = str(mondo_uri)
    prefix = str(MONDO)
    if not uri.startswith(prefix):
        return None

    value = uri.removeprefix(prefix)
    return value if value.isdigit() else None


def omim_id(omim_uri: URIRef) -> str | None:
    match = OMIM_URI_PATTERN.search(str(omim_uri))
    return match.group(1) if match else None


# mondo_uriに対してomim_uriが非推奨の場合は省く
def is_deprecated(graph: Graph, mondo_uri: URIRef) -> bool:
    return any(str(value).lower() == "true" for value in graph.objects(mondo_uri, OWL.deprecated))


def build_mondo_omim_rows(mondo_owl_path: Path) -> list[dict[str, str]]:
    graph = Graph()
    graph.parse(mondo_owl_path, format="xml")

    rows = set()
    for mondo_uri, _, omim_uri in graph.triples((None, SKOS.exactMatch, None)):
        if not isinstance(mondo_uri, URIRef) or not isinstance(omim_uri, URIRef):
            continue

        # くどいかも
        if (mondo_uri, RDF.type, OWL.Class) not in graph:
            continue

        if is_deprecated(graph, mondo_uri):
            continue

        mondo = mondo_id(mondo_uri)
        omim = omim_id(omim_uri)
        if mondo is None or omim is None:
            continue

        rows.add(
            (
                mondo,
                omim,
            )
        )

    return rows


def write_mondo_omim_mapping_csv(config: configparser.ConfigParser) -> int:
    rows = build_mondo_omim_rows(config.data_path)
    fieldnames = ["mondo_id", "omim_id"]

    with open(config.data_path, 'w') as w:
        writer = csv.DictWriter(w, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return

if __name__ == "__main__":
    config_ini = configparser.ConfigParser()

    # mim2geneの取得
    config_ini.read('config.ini', encoding='utf-8')
    disease_gene_omim_helper_config = OMIMGetDataConfig(
        config_ini.get('DEFAULT', 'omim_mim2gene_path'),
        config_ini.get('DEFAULT', 'omim_mim2gene_data_uri'),
        config_ini.get('DEFAULT', 'omim_dir')
    )
    get_data(disease_gene_omim_helper_config)

    # mondo:omimのマップを作成
    write_mondo_omim_mapping_csv(disease_gene_omim_helper_config)
