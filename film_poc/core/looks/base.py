"""Look data model, backend protocol and the default registry.

A backend is any object with ``apply(linear, look) -> display-encoded float32``. Each
backend lives in its own module of this package and registers itself on import; see
``looks/__init__.py``. Backends never read files: data comes through ``core.tables``.
"""
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

DEFAULT_BACKEND = 'fuji'


def display_rgb(linear: np.ndarray) -> np.ndarray:
    """Clip to [0, 1] and apply the sRGB transfer curve."""
    x = np.clip(linear, 0, 1)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)


@dataclass
class Look:
    """One selectable look."""
    display_name: str
    backend: str | None = None  # None means the default (fuji) backend
    origin: str = ''
    detail: str = ''
    params: dict = field(default_factory=dict)  # backend-specific data

    @property
    def backend_id(self) -> str:
        return self.backend or DEFAULT_BACKEND


class LookBackend(Protocol):
    def apply(self, linear: np.ndarray, look: Look) -> np.ndarray: ...


class LookRegistry(MutableMapping):
    """Ordered name -> Look mapping plus the table of backends that render them."""

    def __init__(self) -> None:
        self._looks: dict[str, Look] = {}
        self._backends: dict[str, LookBackend] = {}

    def add_backend(self, backend_id: str, backend: LookBackend) -> None:
        self._backends[backend_id] = backend

    def backend(self, look: Look) -> LookBackend:
        try:
            return self._backends[look.backend_id]
        except KeyError:
            raise ValueError(f'Backend de look desconocido: {look.backend_id}') from None

    def __getitem__(self, name: str) -> Look:
        return self._looks[name]

    def __setitem__(self, name: str, look: Look) -> None:
        self._looks[name] = look

    def __delitem__(self, name: str) -> None:
        del self._looks[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._looks)

    def __len__(self) -> int:
        return len(self._looks)


registry = LookRegistry()
