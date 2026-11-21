"""RAW decoder contract and extension lookup. Adapters implement and register decoders."""
from pathlib import Path
from typing import Protocol

import numpy as np


class RawDecoder(Protocol):
    extensions: tuple[str, ...]  # lowercase, with dot, e.g. ('.arw',)
    label: str                   # shown in the unsupported-file message, e.g. 'Sony .ARW'

    def decode(self, path: Path) -> tuple[np.ndarray, np.ndarray]:
        """Return (linear, reference): oriented HxWx3 float32 linear sRGB in [0, 1] with the
        camera white balance applied, and the embedded camera JPEG preview as HxWx3 uint8."""
        ...


_decoders: dict[str, RawDecoder] = {}


def register_decoder(decoder: RawDecoder) -> None:
    for extension in decoder.extensions:
        _decoders[extension] = decoder


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in _decoders


def supported_labels() -> str:
    return ' / '.join(dict.fromkeys(d.label for d in _decoders.values()))


def supported_extensions() -> tuple[str, ...]:
    return tuple(_decoders)


def decoder_for(path: Path) -> RawDecoder:
    try:
        return _decoders[path.suffix.lower()]
    except KeyError:
        raise ValueError(f'Este POC acepta archivos {supported_labels()}.') from None
