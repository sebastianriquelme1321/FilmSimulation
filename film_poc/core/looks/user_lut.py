"""Imported community LUTs (.cube / HaldCLUT). Looks are added by user_library."""
from pathlib import Path

import numpy as np

from ... import user_library
from ...adapters.storage import library_dir
from .base import display_rgb, registry


class UserLutBackend:
    def apply(self, linear, look):
        return user_library.apply(display_rgb(linear).astype(np.float64), look)

    def bundle_files(self, look) -> list[Path]:
        """The LUT and its library entry, so a RAW archive can restore the look."""
        lut = Path(look['path'])
        entry = library_dir() / (lut.stem + '.entry.json')
        if not entry.is_file():
            raise ValueError('Falta la información local de la LUT para conservar la receta.')
        return [lut, entry]


registry.add_backend('user-lut', UserLutBackend())
