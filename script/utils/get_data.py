from dataclasses import dataclass
from subprocess import PIPE, Popen
import urllib.request
import urllib.error

from utils.log_util import get_logger

logger = get_logger()

@dataclass
class GetDataConfig(object):
    data_path: str
    url: str

def get_data(config: GetDataConfig):
    try:
        urllib.request.urlretrieve(config.url, config.data_path)
    except urllib.error.ContentTooShortError as e:
        logger.error('ContentTooShortError: %s', e)
