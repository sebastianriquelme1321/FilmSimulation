"""Shared 3D-LUT evaluation."""
import numpy as np
from scipy.interpolate import RegularGridInterpolator


def apply_lut3d(rgb: np.ndarray, interpolator: RegularGridInterpolator) -> np.ndarray:
    """Evaluate a 3D LUT on rgb clipped to [0, 1]; return float32 clipped to [0, 1]."""
    values = interpolator(np.clip(rgb, 0, 1).reshape(-1, 3))
    return np.clip(values.reshape(rgb.shape), 0, 1).astype(np.float32)
