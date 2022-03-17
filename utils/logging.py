import logging

from utils.functions import first, find

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"


COLORS = {
    'DEBUG': BLUE,
    'INFO': WHITE,
    'WARNING': YELLOW,
    'CRITICAL': MAGENTA,
    'ERROR': RED
}


class _SimpleFormatter(logging.Formatter):
    def __init__(self, frmt):
        frmt = frmt.replace("$RESET", "").replace("$BOLD", "")
        logging.Formatter.__init__(self, frmt)

    def format(self, record: logging.LogRecord) -> str:
        return logging.Formatter.format(self, record)


class _ColoredFormatter(logging.Formatter):
    def __init__(self, frmt: str):
        frmt = frmt.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
        logging.Formatter.__init__(self, frmt)

    def format(self, record: logging.LogRecord) -> str:
        return COLOR_SEQ % (30 + COLORS[record.levelname]) + logging.Formatter.format(self, record) + RESET_SEQ


FORMAT_STR = "$BOLD%(asctime)s - %(levelname)-8s - [%(module)20s.%(funcName)-20s:%(lineno)4s] - %(message)s"

_colored_formatter = _ColoredFormatter(FORMAT_STR)
_simple_formatter = _SimpleFormatter(FORMAT_STR)

console = logging.StreamHandler()
console.setFormatter(_colored_formatter)

_logger = logging.getLogger("faceit")
_logger.addHandler(console)
_logger.setLevel(logging.DEBUG)


def set_root_log_level(level: int):
    _logger.setLevel(level)


def set_log_level(level: int):
    first(lambda it: isinstance(it, logging.StreamHandler), _logger.handlers).setLevel(level)


def set_log_file(file_path: str, level: int):
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(_simple_formatter)
    file_handler.setLevel(level)
    if find(lambda it: isinstance(it, logging.FileHandler), _logger.handlers) is None:
        _logger.addHandler(file_handler)


def set_file_log_level(level: int):
    first(lambda it: isinstance(it, logging.StreamHandler), _logger.handlers).setLevel(level)


def logger():
    return _logger


