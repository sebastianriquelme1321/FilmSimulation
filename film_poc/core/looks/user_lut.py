"""Imported community LUTs (.cube / HaldCLUT). Looks are added by services/library.py.

The adapter registers the ``'user-lut'`` table loader (path -> (cube, domain_min, domain_max)).
"""
from functools import lru_cache

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .. import tables
from ..lut3d import apply_lut3d
from .base import display_rgb, registry


@lru_cache(maxsize=20)
def _table(path):
    cube, low, high = tables.load('user-lut', path)
    axis = np.linspace(0, 1, len(cube))
    return RegularGridInterpolator((axis, axis, axis), cube, bounds_error=True), low, high


def apply(rgb: np.ndarray, profile: dict) -> np.ndarray:
    """Apply an imported LUT profile to display-sRGB rgb."""
    table, low, high = _table(profile['path'])
    return apply_lut3d((rgb-low)/(high-low), table)


class UserLutBackend:
    def apply(self, linear, look):
        return apply(display_rgb(linear).astype(np.float64), look)


registry.add_backend('user-lut', UserLutBackend())
