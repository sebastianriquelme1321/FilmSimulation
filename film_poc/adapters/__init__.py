"""Everything that touches the outside world (disk, RAW libraries, bundled assets)."""
import importlib
import pkgutil


def load_decoders() -> None:
    """Import every ``*_decoder`` module here; each registers its RawDecoder on import.

    Adding a RAW format is therefore one new file ``adapters/<name>_decoder.py``.
    """
    # The explicit name is a fallback for frozen apps, where iter_modules may find nothing.
    names = {m.name for m in pkgutil.iter_modules(__path__) if m.name.endswith('_decoder')}
    for name in sorted(names | {'rawpy_decoder'}):
        try:
            importlib.import_module(f'{__name__}.{name}')
        except ImportError as exc:
            raise ValueError(f'No se pudo cargar el decodificador RAW «{name}»: {exc}') from exc
