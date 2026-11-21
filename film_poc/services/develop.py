"""Use case: open a RAW file and develop it to tone-matched linear sRGB."""
from pathlib import Path

import numpy as np

from .. import adapters
from ..core import raw
from ..core.tone import match_camera_tone


def decode(path: Path) -> np.ndarray:
    """Oriented HxWx3 float32 linear sRGB, [0,1], tone-matched to the embedded preview."""
    adapters.load_decoders()
    linear, reference = raw.decoder_for(path).decode(path)
    return match_camera_tone(linear, reference)
