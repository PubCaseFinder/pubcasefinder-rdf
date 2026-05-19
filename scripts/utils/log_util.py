import logging

def get_logger():
    logger = logging.getLogger(__name__)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )

    return logger