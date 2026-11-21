"""Approximate film stocks rendered through HaldCLUT tables handed over by an adapter.

The adapter registers the ``'film-stock'`` table loader (stock name -> 64^3x3 cube) and the
stock Looks themselves (see ``adapters/film_stock_files.py``).
"""
from functools import lru_cache

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .. import tables
from ..lut3d import apply_lut3d
from .base import display_rgb, registry


@lru_cache(maxsize=6)
def _interpolator(stock):
    cube = tables.load('film-stock', stock)
    if not np.isfinite(cube).all() or cube.min() < 0 or cube.max() > 1:
        raise ValueError('Invalid film stock LUT')
    axis = np.linspace(0, 1, len(cube))
    return RegularGridInterpolator((axis, axis, axis), cube, bounds_error=True)


def apply(rgb, stock):
    return apply_lut3d(rgb, _interpolator(stock))


class FilmStockBackend:
    def apply(self, linear, look):
        return apply(display_rgb(linear).astype(np.float64), look['stock'])


registry.add_backend('film-stock', FilmStockBackend())
