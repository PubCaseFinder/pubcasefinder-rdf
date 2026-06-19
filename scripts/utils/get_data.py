import urllib.request
import urllib.error
from pathlib import Path

from utils.log_util import get_logger

logger = get_logger()

def download_file(url: str, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "downloading data: url=%s output=%s",
        url,
        output_path,
    )

    try:
        urllib.request.urlretrieve(url, output_path)
    except urllib.error.ContentTooShortError:
        logger.exception("failed to download data")
        raise
    except urllib.error.URLError:
        logger.exception("failed to download data")
        raise

    logger.info("finished downloading data: output=%s", output_path)
    return output_path