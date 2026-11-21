"""RAW decoder contract and extension lookup. Adapters implement and register decoders."""
from pathlib import Path
from typing import Protocol

import numpy as np


class RawDecoder(Protocol):
    extensions: tuple[str, ...]  # lowercase, with dot, e.g. ('.arw',)
    label: str                   # shown in the unsupported-file message, e.g. 'RAW'

    def decode(self, path: Path) -> tuple[np.ndarray, np.ndarray | None]:
        """Return (linear, reference): oriented HxWx3 float32 linear sRGB in [0, 1] with the
        camera white balance applied, and the embedded camera JPEG preview as HxWx3 uint8, or
        None when the file has no usable preview (the tone match is then skipped).
        Failures must raise ValueError with a user-facing Spanish message."""
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


def format_label(path: Path) -> str:
    """Specific format name of a supported file ('JPEG', 'RAW'...): the decoder's optional
    ``format_label(path)``, else its ``label``."""
    decoder = decoder_for(path)
    describe = getattr(decoder, 'format_label', None)
    return describe(path) if describe else decoder.label


def extensions_by_label() -> dict[str, tuple[str, ...]]:
    """Registered extensions grouped by decoder label, in registration order."""
    groups: dict[str, list[str]] = {}
    for extension, decoder in _decoders.items():
        groups.setdefault(decoder.label, []).append(extension)
    return {label: tuple(found) for label, found in groups.items()}


def decoder_for(path: Path) -> RawDecoder:
    try:
        return _decoders[path.suffix.lower()]
    except KeyError:
        raise ValueError(f'Este POC acepta archivos {supported_labels()}.') from None
