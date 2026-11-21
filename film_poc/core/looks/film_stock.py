"""Approximate film stocks rendered through bundled HaldCLUT tables."""
import numpy as np

from ... import film_stocks
from .base import Look, display_rgb, registry


class FilmStockBackend:
    def apply(self, linear, look):
        return film_stocks.apply(display_rgb(linear).astype(np.float64), look['stock'])


registry.add_backend('film-stock', FilmStockBackend())
for _stock, _asset in film_stocks.STOCKS.items():
    registry[f'{_stock} (película aproximada)'] = Look(
        _stock, 'film-stock',
        'spektrafilm / Film Lab' if 'spektrafilm' in _asset['source'] else 'Pat David / HaldCLUT',
        f"{_asset['source']} · {_asset['license']} · aproximación de película",
        {'stock': _stock})
