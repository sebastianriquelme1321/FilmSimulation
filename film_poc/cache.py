"""Disposable local caches; failed/corrupt caches always fall back to calculation."""
import hashlib
from collections.abc import Callable

import numpy as np

from .fileio import atomic_path
from .user_library import library_dir


def cached_array(namespace: str, token: str, build: Callable[[], np.ndarray],
                 shape: tuple[int, ...]) -> np.ndarray:
    """Return the cached array for token, or build it and store it best-effort."""
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
