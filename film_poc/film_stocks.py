"""Display-sRGB film stock LUTs; data licensing is separate from code."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .cache import cached_array
from .hald_loader import load_hald
from .lut3d import apply_lut3d

ASSETS = Path(__file__).parent/'assets'/'film-stocks'
STOCKS = json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=6)
def table(stock):
    cube=cached_array('film-stocks',STOCKS[stock]['sha256'],
                      lambda: load_hald(ASSETS/STOCKS[stock]['file']),(64,64,64,3))
    if not np.isfinite(cube).all() or cube.min()<0 or cube.max()>1:
        raise ValueError('Invalid film stock LUT')
    axis=np.linspace(0,1,len(cube))
    return RegularGridInterpolator((axis,axis,axis),cube,bounds_error=True)


def apply(rgb,stock):
    return apply_lut3d(rgb,table(stock))
