"""Use case: open a RAW file and develop it to tone-matched linear sRGB."""
from pathlib import Path

import numpy as np

from .. import adapters
from ..core import raw
from ..core.tone import match_camera_tone
from .library import install


def decode(path: Path) -> np.ndarray:
    """Oriented HxWx3 float32 linear sRGB, [0,1], tone-matched to the embedded preview
    when there is one (otherwise returned as decoded)."""
    install()
    adapters.load_decoders()
    linear, reference = raw.decoder_for(path).decode(path)
    if reference is None:
        return np.clip(linear, 0.0, 1.0).astype(np.float32, copy=False)
    return match_camera_tone(linear, reference)


def supported_labels() -> str:
    """Labels of the registered RAW formats, e.g. 'RAW'."""
    adapters.load_decoders()
    return raw.supported_labels()


def open_filter() -> str:
    """Qt file-dialog filter for the registered RAW formats."""
    labels = supported_labels()  # loads the decoders first
    patterns = ' '.join(f'*{ext} *{ext.upper()}' for ext in raw.supported_extensions())
    return f'{labels} ({patterns})'
