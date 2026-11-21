import io
import re
from pathlib import Path
from typing import NamedTuple

import numpy as np
import rawpy
from PIL import Image, ImageCms
from scipy.interpolate import PchipInterpolator

from .adapters.storage import atomic_path
from .core import adjustments
from .core.constants import JPEG_QUALITY, REC709_LUMA_F32, STRIP_ROWS
from .core.grain import apply_grain
from .core.looks import registry
from .core.looks.base import display_rgb

LOOKS = registry
PIPELINE_VERSION = 'v4.1-base-adjustments-mix'


def look_slug(name: str) -> str:
    """Return a filesystem-safe slug for the look's display name."""
    profile = LOOKS[name]
    return re.sub(r'[^a-z0-9]+', '_', profile['display_name'].lower()).strip('_')


def render_base(linear: np.ndarray) -> np.ndarray:
    """Display-encode linear sRGB (the common base rendering)."""
    return display_rgb(linear)


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


def decode(path: Path) -> np.ndarray:
    """Adapter contract: oriented HxWx3 float32 linear sRGB, [0,1]."""
    if path.suffix.lower() != '.arw':
        raise ValueError('Este POC acepta archivos Sony .ARW.')
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False,
                              no_auto_bright=True, output_color=rawpy.ColorSpace.sRGB,
                              gamma=(1, 1), output_bps=16)
        try:
            thumb = raw.extract_thumb()
            if isinstance(thumb.data, bytes):
                reference = Image.open(io.BytesIO(thumb.data)).convert('RGB')
            else:
                reference = Image.fromarray(thumb.data).convert('RGB')
            reference.thumbnail((1000, 1000))
        except (rawpy.LibRawError, OSError, ValueError) as exc:
            raise ValueError('Este RAW no contiene una previsualización utilizable '
                             'para la base v3.') from exc
    return match_camera_tone(rgb.astype(np.float32) / 65535, reference)


def apply_look(linear: np.ndarray, name: str) -> np.ndarray:
    """Render linear sRGB through the named look; returns display-encoded float32."""
    look = LOOKS[name]
    return LOOKS.backend(look).apply(linear, look)


class EditSettings(NamedTuple):
    base_name: str
    values: dict


def edit_settings(name: str, exposure_ev: float | None = None, temperature: float | None = None,
                  intensity: float | None = None) -> EditSettings:
    """Resolve and validate edit values (recipe defaults fill in omitted ones)."""
    profile = LOOKS[name]
    recipe = profile.get('recipe', {}) if profile.get('backend') == 'recipe' else {}
    values = {'exposure_ev': recipe.get('exposure_ev', 0) if exposure_ev is None else exposure_ev,
              'temperature': recipe.get('temperature', 0) if temperature is None else temperature,
              'intensity': recipe.get('strength', 1) if intensity is None else intensity}
    adjustments.validate(**values)
    return EditSettings(recipe.get('base_look', name), values)


def render_edit(linear: np.ndarray, name: str, exposure_ev: float | None = None,
                temperature: float | None = None,
                intensity: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return adjusted base and mixed look; both display-encoded sRGB, no grain."""
    base_name, settings = edit_settings(name, exposure_ev, temperature, intensity)
    corrected = adjustments.apply_base(linear, settings['exposure_ev'], settings['temperature'])
    before = render_base(corrected)
    amount = settings['intensity']
    if amount == 0:
        return before, before.copy()
    after = apply_look(corrected, base_name)
    mixed = before*(1-amount) + after*amount
    return before, np.clip(mixed, 0, 1).astype(np.float32)


def uint8(rgb: np.ndarray) -> np.ndarray:
    """Convert display-encoded [0, 1] floats to rounded uint8."""
    return np.rint(np.clip(rgb, 0, 1)*255).astype(np.uint8)


def export_jpeg(linear: np.ndarray, name: str, destination: str | Path, grain: str = 'Desactivado',
                *, exposure_ev: float | None = None, temperature: float | None = None,
                intensity: float | None = None) -> None:
    """Render in strips to limit full-resolution temporary allocations; atomic save."""
    destination = Path(destination)
    if destination.suffix.lower() not in ('.jpg', '.jpeg'):
        raise ValueError('La salida debe ser .jpg o .jpeg.')
    edit_settings(name, exposure_ev, temperature, intensity)
    out = np.empty(linear.shape, dtype=np.uint8)
    for row in range(0, len(linear), STRIP_ROWS):
        _, rgb = render_edit(linear[row:row+STRIP_ROWS], name, exposure_ev, temperature, intensity)
        out[row:row+STRIP_ROWS] = uint8(apply_grain(rgb, grain, origin_y=row))
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    with atomic_path(destination, '.jpg') as temporary:
        Image.fromarray(out).save(temporary, format='JPEG', quality=JPEG_QUALITY, subsampling=0,
                                  icc_profile=icc)
