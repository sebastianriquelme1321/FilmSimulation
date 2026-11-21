"""RAW decoding through rawpy/LibRaw. Auto-registered (see ``adapters/__init__.py``).

Only Sony ARW is verified with real files; the other extensions rely on LibRaw and are
experimental.
"""
import io
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

from ..core.raw import register_decoder

MIN_REFERENCE_SIDE = 64  # smaller embedded previews are useless as a tone reference


def _reference(raw: 'rawpy.RawPy') -> np.ndarray | None:
    """Embedded preview as HxWx3 uint8, or None when missing, tiny or unreadable."""
    try:
        thumb = raw.extract_thumb()
        data = thumb.data
        if isinstance(data, (bytes, bytearray)):
            image = Image.open(io.BytesIO(bytes(data)))
        else:
            image = Image.fromarray(np.asarray(data))
        image = image.convert('RGB')
        if max(image.size) < MIN_REFERENCE_SIDE:
            return None
        image.thumbnail((1000, 1000))
        return np.asarray(image)
    except (rawpy.LibRawError, OSError, ValueError, TypeError, AttributeError,
            MemoryError, Image.DecompressionBombError):
        return None


class RawpyDecoder:
    extensions = ('.arw', '.srf', '.sr2', '.cr2', '.cr3', '.crw', '.nef', '.nrw', '.raf',
                  '.rw2', '.orf', '.pef', '.dng', '.srw', '.3fr', '.iiq', '.erf', '.mrw',
                  '.kdc', '.dcr', '.raw')
    label = 'RAW'

    def decode(self, path: Path) -> tuple[np.ndarray, np.ndarray | None]:
        """Oriented HxWx3 float32 linear sRGB in [0, 1] plus the embedded preview (uint8 RGB),
        or None when the file has no usable preview."""
        try:
            with rawpy.imread(str(path)) as raw:
                rgb = raw.postprocess(use_camera_wb=True, use_auto_wb=False,
                                      no_auto_bright=True, output_color=rawpy.ColorSpace.sRGB,
                                      gamma=(1, 1), output_bps=16)
                reference = _reference(raw)
        except (rawpy.LibRawError, OSError, ValueError, MemoryError) as exc:
            raise ValueError(
                f'No se pudo abrir «{Path(path).name}»: el archivo está dañado o el formato '
                'o el modelo de cámara no es compatible con esta versión. Puedes reportar el '
                'modelo de tu cámara desde Ayuda > Enviar feedback.') from exc
        return rgb.astype(np.float32) / 65535, reference


register_decoder(RawpyDecoder())
