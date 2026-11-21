"""Tone matching of a decoded RAW to its embedded camera preview."""
import numpy as np
from scipy.interpolate import PchipInterpolator

from .constants import REC709_LUMA_F32, STRIP_ROWS


def match_camera_tone(linear: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Match luminance quantiles to the embedded JPEG, preserving RAW detail.

    Reference color is not copied. Quantile mapping is approximate when crops
    differ; bounds limit extreme lifts. Input/output remain linear sRGB.
    """
    x = np.clip(np.asarray(linear, dtype=np.float32), 0, 1)
    weights = REC709_LUMA_F32
    step = max(1, max(x.shape[:2]) // 1000)
    sample = x[::step, ::step] @ weights
    ref = np.asarray(reference, dtype=np.float32) / 255
    ref = np.where(ref <= .04045, ref/12.92, ((ref+.055)/1.055)**2.4)
    ref_y = ref @ weights
    percentiles = [1, 5, 10, 20, 35, 50, 65, 80, 90, 95, 99]
    src = np.percentile(sample, percentiles)
    dst = np.percentile(ref_y, percentiles)
    # Require enough distinct luminance levels; avoid invented contrast in flat frames.
    keep = (src > 1e-5) & (src < .999)
    src, dst = src[keep], dst[keep]
    unique = np.r_[True, np.diff(src) > 1e-5]
    src, dst = src[unique], dst[unique]
    if len(src) < 3 or src[-1]-src[0] < .005:
        return x.copy()
    dst = np.minimum(np.maximum(dst, src*.5), src*4)
    dst = np.maximum.accumulate(np.clip(dst, 0, 1))
    curve = PchipInterpolator(np.r_[0, src, 1], np.r_[0, dst, 1])
    result = np.empty_like(x)
    for row in range(0, len(x), STRIP_ROWS):
        block = x[row:row+STRIP_ROWS]
        y = block @ weights
        target = curve(y).astype(np.float32)
        rgb = block * (target / np.maximum(y, 1e-10))[..., None]
        chroma = rgb-target[..., None]
        amount = np.minimum(1, (1-target)/np.maximum(chroma.max(axis=-1), 1e-10))
        result[row:row+STRIP_ROWS] = np.clip(target[..., None]+chroma*amount[..., None], 0, 1)
    return result
