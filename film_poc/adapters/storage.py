"""Local disk access: per-user library folder, atomic writes, array cache and preferences."""
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

import numpy as np


def library_dir() -> Path:
    """Return the per-user FilmPOC data directory (FILM_POC_USER_DIR overrides)."""
    if os.environ.get('FILM_POC_USER_DIR'):
        return Path(os.environ['FILM_POC_USER_DIR'])
    if sys.platform == 'darwin':
        return Path.home()/'Library'/'Application Support'/'FilmPOC'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local'))/'FilmPOC'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local'/'share'))/'FilmPOC'


@contextmanager
def atomic_path(destination: str | Path, suffix: str = '.tmp') -> Iterator[Path]:
    """Yield a temp path beside destination; os.replace it on success, always clean up."""
    destination = Path(destination)
    fd, name = tempfile.mkstemp(suffix=suffix, dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        yield temporary
        os.replace(temporary, destination)
    finally:
        with suppress(OSError):
            temporary.unlink()


def cached_array(namespace: str, token: str, build: Callable[[], np.ndarray],
                 shape: tuple[int, ...]) -> np.ndarray:
    """Disposable disk cache; failed/corrupt entries always fall back to calculation."""
    name = hashlib.sha256(token.encode()).hexdigest() + '.npy'
    path = library_dir() / 'cache' / namespace / name
    try:
        result = np.load(path, allow_pickle=False, mmap_mode='r')
        valid_dtype = result.dtype in (np.dtype('float32'), np.dtype('float64'))
        if result.shape == shape and valid_dtype and np.isfinite(result).all():
            return result
    except (OSError, ValueError, EOFError):
        pass
    result = build()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with atomic_path(path, '.npy') as temporary:
            with temporary.open('wb') as stream:
                np.save(stream, result, allow_pickle=False)
    except OSError:
        pass
    return result


def load_theme_name() -> str | None:
    """Return the saved theme name string, or None if missing or unreadable."""
    try:
        data = json.loads((library_dir() / 'appearance.json').read_text(encoding='utf-8'))
        theme = data.get('theme') if isinstance(data, dict) else None
        return theme if isinstance(theme, str) else None
    except (OSError, ValueError, TypeError):
        return None


def save_theme_name(theme: str) -> None:
    """Persist the theme name atomically."""
    root = library_dir()
    root.mkdir(parents=True, exist_ok=True)
    with atomic_path(root / 'appearance.json') as temporary:
        temporary.write_text(json.dumps({'theme': theme}), encoding='utf-8')
