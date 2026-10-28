"""Display-sRGB film stock LUTs; data licensing is separate from code."""
from functools import lru_cache
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from .hald_loader import load_hald

ASSETS = Path(__file__).parent/'assets'/'film-stocks'
STOCKS = json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=6)
def table(stock):
    cube=load_hald(ASSETS/STOCKS[stock]['file'])
    if not np.isfinite(cube).all() or cube.min()<0 or cube.max()>1:
        raise ValueError('Invalid film stock LUT')
    axis=np.linspace(0,1,len(cube))
    return RegularGridInterpolator((axis,axis,axis),cube,bounds_error=True)


def apply(rgb,stock):
    return np.clip(table(stock)(np.clip(rgb,0,1).reshape(-1,3)).reshape(rgb.shape),0,1).astype(np.float32)
