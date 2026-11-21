"""Small pre-look linear RGB corrections, relative to the decoded camera WB."""
import numpy as np

from .constants import REC709_LUMA_F32


def validate(exposure_ev: float = 0, temperature: float = 0, intensity: float = 1,
             contrast: float = 0, saturation: float = 0, tint: float = 0) -> None:
    """Raise ValueError unless the adjustments are finite and in range."""
    values = (exposure_ev, temperature, intensity, contrast, saturation, tint)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x)
               for x in values):
        raise ValueError('Los ajustes deben ser números finitos.')
    if (not -3 <= exposure_ev <= 3 or not 0 <= intensity <= 1
            or any(not -100 <= x <= 100 for x in (temperature, contrast, saturation, tint))):
        raise ValueError('Ajustes fuera de rango: exposición ±3 EV, temperatura ±100, '
                         'contraste ±100, saturación ±100, tinte ±100 e intensidad 0–1.')


def apply_base(linear: np.ndarray, exposure_ev: float = 0, temperature: float = 0,
               contrast: float = 0, saturation: float = 0, tint: float = 0) -> np.ndarray:
    """Apply exposure, warmth, tint, contrast and saturation to linear RGB (clipped float32)."""
    validate(exposure_ev, temperature, contrast=contrast, saturation=saturation, tint=tint)
    # Relative warm/cool RGB correction, not a Kelvin-calibrated sensor WB.
    shift = temperature / 100
    gains = np.array([2**(.35*shift), 1, 2**(-.35*shift)], dtype=np.float32)
    gains /= gains @ REC709_LUMA_F32
    out = np.clip(np.asarray(linear, dtype=np.float32) * gains * (2**exposure_ev), 0, 1)
    if tint:
        # Relative green (-) <-> magenta (+) shift, luma-preserving.
        shift = tint / 100
        gains = np.array([2**(.2*shift), 2**(-.4*shift), 2**(.2*shift)], dtype=np.float32)
        gains /= gains @ REC709_LUMA_F32
        out = np.clip(out * gains, 0, 1)
    if contrast:
        # Power curve around linear mid-gray; monotonic, fixes 0 and 1.
        out = np.clip(.18 * (out / .18)**np.float32(2**(contrast / 100)), 0, 1)
    if saturation:
        luma = (out @ REC709_LUMA_F32)[..., None]
        out = np.clip(luma + (out - luma) * np.float32(1 + saturation / 100), 0, 1)
    return out.astype(np.float32, copy=False)
