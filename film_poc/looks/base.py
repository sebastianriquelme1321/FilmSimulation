"""Look data model, backend protocol and the default registry.

A backend is any object with ``apply(linear, look) -> display-encoded float32``
and, optionally, ``bundle_files(look) -> list[Path]`` (extra files that must
travel with a RAW archive). Each backend lives in its own module of this
package and registers itself on import; see ``looks/__init__.py``.
"""
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np

DEFAULT_BACKEND = 'fuji'
_FIELDS = ('display_name', 'backend', 'origin', 'detail')


def display_rgb(linear: np.ndarray) -> np.ndarray:
    """Clip to [0, 1] and apply the sRGB transfer curve."""
    x = np.clip(linear, 0, 1)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)


@dataclass
class Look:
    """One selectable look. Also readable like the legacy profile dict."""
    display_name: str
    backend: str | None = None  # None means the default (fuji) backend
    origin: str = ''
    detail: str = ''
    params: dict = field(default_factory=dict)  # backend-specific data

    @classmethod
    def from_profile(cls, profile: dict) -> 'Look':
        known = {k: profile[k] for k in _FIELDS if k in profile}
        return cls(params={k: v for k, v in profile.items() if k not in _FIELDS}, **known)

    @property
    def backend_id(self) -> str:
        return self.backend or DEFAULT_BACKEND

    def __getitem__(self, key: str) -> Any:
        if key in _FIELDS:
            return getattr(self, key)
        return self.params[key]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


class LookBackend(Protocol):
    def apply(self, linear: np.ndarray, look: Look) -> np.ndarray: ...
    # Optional: def bundle_files(self, look: Look) -> list[Path]


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

    def bundle_files(self, look: Look) -> list[Path]:
        hook = getattr(self.backend(look), 'bundle_files', None)
        return hook(look) if hook else []

    def register(self, name: str, look: Look | dict) -> None:
        self[name] = look

    def all(self) -> list[Look]:
        return list(self._looks.values())

    def names(self) -> list[str]:
        return list(self._looks)

    def copy(self) -> dict:
        return dict(self._looks)

    def __getitem__(self, name: str) -> Look:
        return self._looks[name]

    def __setitem__(self, name: str, look: Look | dict) -> None:
        self._looks[name] = look if isinstance(look, Look) else Look.from_profile(look)

    def __delitem__(self, name: str) -> None:
        del self._looks[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._looks)

    def __len__(self) -> int:
        return len(self._looks)


registry = LookRegistry()
