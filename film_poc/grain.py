"""Deterministic monochromatic output grain; not a measured film stock model."""
import numpy as np

GRAIN = {'Desactivado': 0.0, 'Suave': .018, 'Fuerte': .055}
_SIZE = {'Suave': 2, 'Fuerte': 6}


def _noise(rows, cols):
    h = rows*np.uint32(374761393)+cols*np.uint32(668265263)+np.uint32(20261027)
    h = (h ^ (h >> 13))*np.uint32(1274126177)
    h ^= h >> 16
    u = ((h & 65535).astype(np.float32)+.5)/65536
    v = ((h >> 16).astype(np.float32)+.5)/65536
    return np.sqrt(-2*np.log(u))*np.cos(2*np.pi*v)


def apply_grain(rgb, mode='Desactivado', origin_y=0, step=1):
    strength = GRAIN[mode]
    if not strength:
        return rgb
    height,width = rgb.shape[:2]
    # Coordinates in the full-resolution image keep strips/preview consistent.
    rows = (np.arange(height,dtype=np.uint32)*step+origin_y)[:,None]
    cols = (np.arange(width,dtype=np.uint32)*step)[None,:]
    size = _SIZE[mode]
    iy, ix = rows//size, cols//size
    fy, fx = (rows % size).astype(np.float32)/size, (cols % size).astype(np.float32)/size
    # Smooth correlated grain avoids square cells and remains aligned in strips.
    fy, fx = fy*fy*(3-2*fy), fx*fx*(3-2*fx)
    top = _noise(iy,ix)*(1-fx)+_noise(iy,ix+np.uint32(1))*fx
    bottom = _noise(iy+np.uint32(1),ix)*(1-fx)+_noise(iy+np.uint32(1),ix+np.uint32(1))*fx
    noise = (top*(1-fy)+bottom*fy)*1.3
    y = np.sum(rgb*np.array([.2126,.7152,.0722],dtype=np.float32),axis=-1)
    weight = .25+.75*np.sin(np.pi*np.clip(y,0,1))
    return np.clip(rgb+(strength*weight*noise)[...,None],0,1).astype(np.float32)
