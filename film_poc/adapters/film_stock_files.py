"""Bundled film-stock HaldCLUT assets: manifest, table loading and Look registration."""
import json
import logging
from functools import lru_cache
from pathlib import Path

from ..core import tables
from ..core.looks import Look, LookRegistry
from .hald_loader import load_hald
from .storage import cached_array

ASSETS = Path(__file__).parents[1]/'assets'/'film-stocks'
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def manifest() -> dict:
    """The stock manifest. A missing or corrupt bundle is a packaging bug: fail loudly.

    Exceptions are not cached by lru_cache, so a later call retries."""
    try:
        return json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        log.error('Film stock manifest unavailable: %s', ASSETS/'manifest.json')
        raise RuntimeError(f'Faltan los recursos de películas ({ASSETS/"manifest.json"}): '
                           'reinstala la aplicación.') from exc


def load_cube(stock: str):
    """Return the stock's 64^3x3 cube, through the disk cache."""
    info = manifest()[stock]
    return cached_array('film-stocks', info['sha256'],
                        lambda: load_hald(ASSETS/info['file']), (64, 64, 64, 3))


def register(registry: LookRegistry) -> None:
    """Hand the table loader to the core and add one Look per bundled stock."""
    tables.register_loader('film-stock', load_cube)
    for stock, asset in manifest().items():
        registry[f'{stock} (película aproximada)'] = Look(
            stock, 'film-stock',
            ('spektrafilm / Film Lab' if 'spektrafilm' in asset['source']
             else 'Pat David / HaldCLUT'),
            f"{asset['source']} · {asset['license']} · aproximación de película",
            {'stock': stock})
