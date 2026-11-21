"""Everything that touches the outside world (disk, RAW libraries, bundled assets)."""
import importlib
import pkgutil


def load_decoders() -> None:
    """Import every ``*_decoder`` module here; each registers its RawDecoder on import.

    Adding a RAW format is therefore one new file ``adapters/<name>_decoder.py``.
    """
    for module in pkgutil.iter_modules(__path__):
        if module.name.endswith('_decoder'):
            importlib.import_module(f'{__name__}.{module.name}')
