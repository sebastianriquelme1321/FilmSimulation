"""Sony ARW decoding through rawpy/LibRaw. Auto-registered (see ``adapters/__init__.py``)."""
import io
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

from ..core.raw import register_decoder


class ArwDecoder:
    extensions = ('.arw',)
    label = 'Sony .ARW'

    def decode(self, path: Path) -> tuple[np.ndarray, np.ndarray]:
        """Oriented HxWx3 float32 linear sRGB in [0, 1] plus the embedded JPEG (uint8 RGB)."""
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
        return rgb.astype(np.float32) / 65535, np.asarray(reference)


register_decoder(ArwDecoder())
