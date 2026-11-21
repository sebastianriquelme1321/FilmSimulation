"""Local log file: rotating handler, uncaught-exception hook and tail reader."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .storage import library_dir

LOG_NAME = 'film_poc.log'
MAX_BYTES = 512 * 1024
BACKUPS = 2
FORMAT = '%(asctime)s %(levelname)-7s %(name)s: %(message)s'


def log_dir() -> Path:
    """Folder holding the log files (inside the per-user library)."""
    return library_dir()/'logs'


def log_path() -> Path:
    return log_dir()/LOG_NAME


def setup_logging() -> Path:
    """Attach the rotating file handler to the 'film_poc' logger (idempotent)."""
    path = log_path()
    logger = logging.getLogger('film_poc')
    logger.setLevel(logging.INFO)
    for handler in list(logger.handlers):
        if getattr(handler, '_film_poc', False):
            if Path(handler.baseFilename) == path.resolve():
                return path
            logger.removeHandler(handler)
            handler.close()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUPS,
                                      encoding='utf-8')
    except OSError:
        return path  # logging is best effort; never block the app
    handler._film_poc = True
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    return path


def install_excepthook(notify=None) -> None:
    """Log uncaught exceptions, call notify(exc) if given, then chain to the previous hook."""
    previous = sys.excepthook

    def hook(exc_type, exc, tb):
        logging.getLogger('film_poc.crash').critical('Uncaught exception',
                                                     exc_info=(exc_type, exc, tb))
        if notify is not None and not issubclass(exc_type, KeyboardInterrupt):
            try:
                notify(exc)
            except Exception:  # the hook must never raise
                pass
        previous(exc_type, exc, tb)

    sys.excepthook = hook


def tail_log(max_chars: int = 3000) -> str:
    """Last max_chars characters of the current log ('' if there is none)."""
    try:
        text = log_path().read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''
    return text[-max_chars:] if max_chars > 0 else ''
