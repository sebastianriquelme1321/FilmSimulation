"""Use case: render the edited image at full resolution and save it as a JPEG."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from ..adapters.storage import atomic_path
from ..core.constants import JPEG_QUALITY, STRIP_ROWS
from ..core.grain import apply_grain
from ..core.render import edit_settings, render_edit, uint8
from .library import install


def export_jpeg(linear: np.ndarray, name: str, destination: str | Path, grain: str = 'Desactivado',
                *, exposure_ev: float | None = None, temperature: float | None = None,
                intensity: float | None = None) -> None:
    """Render in strips to limit full-resolution temporary allocations; atomic save."""
    install()
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
