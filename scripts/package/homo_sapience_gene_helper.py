from __future__ import annotations

from pathlib import Path
import urllib.error
import urllib.request

from package.rdf_build_support import load_config
from utils.log_util import get_logger

logger = get_logger()


def download_homo_sapiens_gene_info(url: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "downloading NCBI Homo sapiens gene_info: url=%s output=%s",
        url,
        output_path,
    )

    try:
        urllib.request.urlretrieve(url, output_path)
    except urllib.error.ContentTooShortError:
        logger.exception("failed to download complete NCBI gene_info file")
        raise
    except urllib.error.URLError:
        logger.exception("failed to download NCBI gene_info file")
        raise

    logger.info("finished downloading NCBI Homo sapiens gene_info: output=%s", output_path)
    return output_path


def main() -> None:
    config = load_config("config.ini")
    download_homo_sapiens_gene_info(
        config["ncbi_homosapience_gene_data_uri"],
        config["ncbigene_file_path"],
    )


if __name__ == "__main__":
    main()
