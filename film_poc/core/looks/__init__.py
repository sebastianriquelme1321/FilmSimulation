"""Look registry. To add a backend, write one module here and import it below.

Film stocks are appended by services.library.install(), so they come last.
(The recipe backend is registered by ``core/render.py`` because it renders through it.)
"""
from . import fuji, darktable, film_stock, user_lut  # noqa: F401,I001  (import order = LOOKS order)
from .base import Look, LookBackend, LookRegistry, registry

__all__ = ['Look', 'LookBackend', 'LookRegistry', 'registry']
