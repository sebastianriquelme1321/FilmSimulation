# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from darktable src/iop/colorchecker.c.
# Copyright (C) 2016-2026 darktable developers.
# Distributed without warranty; see ../LICENSE and THIRD_PARTY_NOTICES.md.
"""Experimental port of the Classic Chrome Lab patch mapping.

Uses SciPy's equivalent thin-plate spline with affine polynomial, evaluated
through a cached display-sRGB LUT. It is not the complete darktable pipeline.
"""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator, RegularGridInterpolator
from .cache import cached_array
import hashlib

NAME = 'Classic Chrome · darktable (experimental)'
PRESETS = {'chrome': 'Classic Chrome', 'astia': 'Astia', 'mchrome': 'Monochrome',
           'provia': 'Provia', 'velvia': 'Velvia'}
_WHITE = np.array([.9642, 1, .8249])
# Linear sRGB to XYZ adapted to D50 (ICC PCS).
_MATRIX = np.array([[.4360747,.3850649,.1430804],
                    [.2225045,.7168786,.0606169],
                    [.0139322,.0971045,.7141733]])
_INVERSE = np.linalg.inv(_MATRIX)


def to_lab(rgb):
    x = np.asarray(rgb,dtype=np.float64)
    linear = np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
    xyz = (linear @ _MATRIX.T)/_WHITE
    delta = 6/29
    f = np.where(xyz>delta**3,np.cbrt(xyz),xyz/(3*delta**2)+4/29)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],axis=-1)


def from_lab(lab):
    y=(lab[...,0]+16)/116
    f=np.stack([y+lab[...,1]/500,y,y-lab[...,2]/200],axis=-1)
    delta=6/29
    xyz=np.where(f>delta,f**3,3*delta**2*(f-4/29))*_WHITE
    linear=xyz @ _INVERSE.T
    rgb=np.where(linear<=.0031308,12.92*linear,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    return np.clip(rgb,0,1)


def patches(preset='chrome'):
    if preset not in PRESETS:
        raise ValueError(f'Unknown darktable preset: {preset}')
    data=json.loads(Path(__file__).with_name(f'darktable_{preset}.json').read_text(encoding='utf-8'))
    return np.array(data['source']),np.array(data['target'])


@lru_cache(maxsize=5)
def mapping(preset='chrome'):
    source,target=patches(preset)
    # r² log(r²) in darktable is 2*r² log(r); coefficient fitting absorbs 2.
    return RBFInterpolator(source,target,kernel='thin_plate_spline',degree=1,smoothing=0)


def direct(rgb, preset='chrome'):
    shape=rgb.shape
    return from_lab(mapping(preset)(to_lab(rgb).reshape(-1,3))).reshape(shape)


@lru_cache(maxsize=5)
def lut(preset='chrome'):
    axis=np.linspace(0,1,49)
    def build():
        grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1)
        values=np.empty_like(grid)
        for i in range(len(axis)):
            values[i]=direct(grid[i],preset)
        return values
    token=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name(f'darktable_{preset}.json').read_bytes()).hexdigest()
    values=cached_array('darktable',token,build,(49,49,49,3))
    return RegularGridInterpolator((axis,axis,axis),values,bounds_error=True)


def apply(rgb, preset='chrome'):
    return np.clip(lut(preset)(np.clip(rgb,0,1).reshape(-1,3)).reshape(rgb.shape),0,1).astype(np.float32)
