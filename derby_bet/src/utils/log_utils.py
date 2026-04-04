# Imports
from pathlib import Path
import logging

from derby_bet.src.utils.io_tools import find_project_root

_BASE_DIR = find_project_root()


def setup_logger(name, level=logging.INFO, console=False, file=False, filename='out.log'):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt='%Y/%m/%d %H:%M:%S.%f'
    )

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if file:
        file_out = Path(_BASE_DIR, 'derby_bet', 'log', filename)
        _check_logger_file(file_out)
        file_handler = logging.FileHandler(file_out)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _check_logger_file(filename):
    if not Path(filename).parent.exists():
        Path(filename).parent.mkdir(parents=True)
    
    if Path(filename).exists():
        with open(str(filename), 'w') as file:
            file.write('')
    
    