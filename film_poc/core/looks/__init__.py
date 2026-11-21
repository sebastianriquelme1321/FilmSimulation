"""Look registry. To add a backend, write one module here and import it below."""
from . import fuji, darktable, film_stock, user_lut, recipe  # noqa: F401,I001  (order = LOOKS order)
from .base import Look, LookBackend, LookRegistry, registry

__all__ = ['Look', 'LookBackend', 'LookRegistry', 'registry']
