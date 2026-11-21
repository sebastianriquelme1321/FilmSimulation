"""Bundled darktable Lab patch data."""
import json
from pathlib import Path

from ..core import tables
from .storage import cached_array

DATA = Path(__file__).parents[1]/'assets'/'darktable'


def load_patches(preset: str) -> tuple[list, list]:
    """Return the (source, target) Lab patch lists of a preset."""
    data = json.loads((DATA/f'darktable_{preset}.json').read_text(encoding='utf-8'))
    return data['source'], data['target']


def register() -> None:
    """Hand the patch loader and the disk array cache to the core."""
    tables.register_loader('darktable', load_patches)
    tables.set_array_cache(cached_array)
