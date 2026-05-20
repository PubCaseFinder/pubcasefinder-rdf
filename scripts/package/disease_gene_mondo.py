from __future__ import annotations

from pathlib import Path

from utils.log_util import get_logger
from rdf_build_support import (
    load_config
)
from scripts.package.disease_gene_association_util import (
    GENCC_SOURCE_URI,
    build_mondo_gene_associations,
    write_gene_association_ttl,
)

logger = get_logger()

def main() -> None:
    config = load_config('config.ini')
    mondo_ncbi_gene_map = build_mondo_gene_associations()
    print(f"MONDO_Gene_Association Count : {len(mondo_ncbi_gene_map)}")

    source_uri_map = {
        "MedGen": "ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen",
        "Orphanet": "http://www.orphadata.org/data/xml/en_product6.xml",
        "GenCC": GENCC_SOURCE_URI,
    }
    write_gene_association_ttl(
        config['rdf_output_dir'] / "MONDO_Gene_Association.ttl",
        mondo_ncbi_gene_map,
        "MONDO",
        "obo:MONDO_",
        "PREFIX obo: <http://purl.obolibrary.org/obo/>",
        source_uri_map,
    )


if __name__ == "__main__":
    main()
