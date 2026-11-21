"""Hooks through which adapters hand loaded data to the pure core.

The core never opens files. Adapters register a loader per kind of data at startup
(``register_loader('film-stock', fn)``) and, optionally, a disposable array cache; the
look backends then ask for data with ``load(kind, key)``.
"""
from collections.abc import Callable
from typing import Any

import numpy as np

_loaders: dict[str, Callable[[str], Any]] = {}


def register_loader(kind: str, loader: Callable[[str], Any]) -> None:
    _loaders[kind] = loader


def load(kind: str, key: str) -> Any:
    """Return the data the adapter registered for (kind, key)."""
    try:
        loader = _loaders[kind]
    except KeyError:
        raise RuntimeError(f'No hay cargador de datos registrado para «{kind}».') from None
    return loader(key)


def _no_cache(namespace: str, token: str, build: Callable[[], np.ndarray],
              shape: tuple[int, ...]) -> np.ndarray:
    return build()


_array_cache: Callable[..., np.ndarray] = _no_cache


def set_array_cache(cache: Callable[..., np.ndarray]) -> None:
    """Install a ``cache(namespace, token, build, shape)`` callable (default: no cache)."""
    global _array_cache
    _array_cache = cache


def cached_array(namespace: str, token: str, build: Callable[[], np.ndarray],
                 shape: tuple[int, ...]) -> np.ndarray:
    """Return build() result, through the installed cache if there is one."""
    return _array_cache(namespace, token, build, shape)
