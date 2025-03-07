# This file can be empty or contain package initialization code if needed.
import logging


# Configure logging
class CustomFormatter(logging.Formatter):
    grey = "\x1b[38m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    cyan = "\x1b[36m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(levelname)s - %(message)s" + reset,
        logging.INFO: cyan + "%(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(levelname)s - %(message)s" + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


global logger
global LOG_LEVEL
LOG_LEVEL = "DEBUG"
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))
ch = logging.StreamHandler()
ch.setLevel(getattr(logging, LOG_LEVEL))
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)
