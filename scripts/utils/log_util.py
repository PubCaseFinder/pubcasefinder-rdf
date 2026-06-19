import inspect
import logging

def get_logger(name=None):
    if name is None:
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        name = caller.f_globals.get('__name__', __name__) if caller is not None else __name__

    logger = logging.getLogger(name)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )

    return logger
