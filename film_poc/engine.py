from pathlib import Path
import os
import tempfile
import io
import re
from copy import deepcopy

import numpy as np
from PIL import Image, ImageCms
import rawpy
from scipy.interpolate import PchipInterpolator
from .profiles import PROFILES
from .profile_transforms import apply_film_simulation, apply_base_saturation
from . import darktable_look
from .grain import apply_grain
from . import film_stocks
from . import user_library


LOOKS = {
    "Classic Chrome (aproximación)": PROFILES['Classic Chrome'],
    "Classic Negative (aproximación)": PROFILES['Classic Neg'],
    **{f"{profile['display_name']} (aproximación)": profile
       for key, profile in PROFILES.items() if key not in ('Classic Chrome', 'Classic Neg')},
}
# Local approximations of the six monochrome color-filter variants. Neutral
# inputs remain neutral; only the RGB contribution to monochrome changes.
for _key, _label in (('Acros', 'ACROS'), ('Mono', 'Monochrome')):
    for _filter, _weights in (('Ye', [.30,.60,.10]), ('R', [.60,.32,.08]), ('G', [.18,.74,.08])):
        _profile = deepcopy(PROFILES[_key])
        _profile['display_name'] = f'{_label} + {_filter}'
        _profile['color_matrix'] = [list(_weights) for _ in range(3)]
        LOOKS[f'{_label} + {_filter} (aproximación)'] = _profile
for _preset, _label in darktable_look.PRESETS.items():
    LOOKS[f'{_label} · darktable (experimental)'] = {
        'display_name': f'{_label} darktable', 'backend': 'darktable', 'preset': _preset}
for _stock in film_stocks.STOCKS:
    LOOKS[f'{_stock} (película aproximada)'] = {
        'display_name': _stock, 'backend': 'film-stock', 'stock': _stock}
PIPELINE_VERSION = 'v3.6-kodak-and-ilford'


def look_slug(name):
    profile = LOOKS[name]
    return re.sub(r'[^a-z0-9]+', '_', profile['display_name'].lower()).strip('_')

# Monotone, scene-independent base rendering: retain black, lift midtones,
# compress toward white. Applied once before the display-referred profiles.
_BASE_CURVE = PchipInterpolator(
    [0, .001, .003, .01, .03, .06, .12, .25, .5, 1],
    [0, .001, .004, .02, .07, .135, .25, .44, .7, 1])


def render_base(linear):
    return display_rgb(linear)


def match_camera_tone(linear, reference):
    """Match luminance quantiles to the embedded JPEG, preserving RAW detail.

    Reference color is not copied. Quantile mapping is approximate when crops
    differ; bounds limit extreme lifts. Input/output remain linear sRGB.
    """
    x = np.clip(np.asarray(linear, dtype=np.float32), 0, 1)
    weights = np.array([.2126, .7152, .0722], dtype=np.float32)
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
    for row in range(0, len(x), 256):
        block = x[row:row+256]
        y = block @ weights
        target = curve(y).astype(np.float32)
        rgb = block * (target / np.maximum(y, 1e-10))[..., None]
        chroma = rgb-target[..., None]
        amount = np.minimum(1, (1-target)/np.maximum(chroma.max(axis=-1), 1e-10))
        result[row:row+256] = np.clip(target[..., None]+chroma*amount[..., None], 0, 1)
    return result


def legacy_base_v2(linear):
    """Retained solely for comparing the previous experimental rendering."""
    x = np.clip(np.asarray(linear, dtype=np.float32), 0, 1)
    y = x @ np.array([.2126, .7152, .0722], dtype=np.float32)
    target = _BASE_CURVE(y).astype(np.float32)
    rgb = x * (target / np.maximum(y, 1e-10))[..., None]
    # Compress chroma only when needed to keep RGB inside the output gamut.
    chroma = rgb - target[..., None]
    maximum = np.max(chroma, axis=-1)
    amount = np.minimum(1, (1-target) / np.maximum(maximum, 1e-10))
    rgb = target[..., None] + chroma * amount[..., None]
    return display_rgb(np.clip(rgb, 0, 1))


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
            reference = (Image.open(io.BytesIO(thumb.data)).convert('RGB')
                         if isinstance(thumb.data, bytes) else Image.fromarray(thumb.data).convert('RGB'))
            reference.thumbnail((1000, 1000))
        except (rawpy.LibRawError, OSError, ValueError) as exc:
            raise ValueError('Este RAW no contiene una previsualización utilizable para la base v3.') from exc
    return match_camera_tone(rgb.astype(np.float32) / 65535, reference)


def display_rgb(linear):
    x = np.clip(linear, 0, 1)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)


def apply_look(linear, name):
    profile = LOOKS[name]
    x = render_base(linear).astype(np.float64)
    if profile.get('backend') == 'darktable':
        return darktable_look.apply(x,profile['preset'])
    if profile.get('backend') == 'film-stock':
        return film_stocks.apply(x,profile['stock'])
    if profile.get('backend') == 'user-lut':
        return user_library.apply(x,profile)
    if profile.get('backend') == 'recipe':
        recipe=profile['recipe']
        transformed=apply_look(linear,recipe['base_look'])
        strength=recipe.get('strength',1.0)
        return np.clip(x*(1-strength)+transformed*strength,0,1).astype(np.float32)
    rgb = apply_film_simulation(x.reshape(-1, 3), profile)
    # Upstream Sepia has saturation=0, which erases its warm matrix/tints.
    if profile['display_name'] != 'Sepia':
        rgb = apply_base_saturation(rgb, profile['base_saturation'])
    return np.clip(rgb.reshape(x.shape), 0, 1).astype(np.float32)


def uint8(rgb):
    return np.rint(np.clip(rgb, 0, 1)*255).astype(np.uint8)


def export_jpeg(linear, name, destination, grain='Desactivado'):
    """Render in strips to limit full-resolution temporary allocations; atomic save."""
    destination = Path(destination)
    if destination.suffix.lower() not in ('.jpg', '.jpeg'):
        raise ValueError('La salida debe ser .jpg o .jpeg.')
    out = np.empty(linear.shape, dtype=np.uint8)
    for row in range(0, len(linear), 256):
        rgb = apply_look(linear[row:row+256], name)
        out[row:row+256] = uint8(apply_grain(rgb, grain, origin_y=row))
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    fd, temp = tempfile.mkstemp(suffix='.jpg', dir=destination.parent)
    os.close(fd)
    try:
        Image.fromarray(out).save(temp, quality=95, subsampling=0, icc_profile=icc)
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
