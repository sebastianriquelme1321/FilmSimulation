"""Everything that touches the outside world (disk, RAW libraries, bundled assets)."""
import importlib
import pkgutil
import threading

_loaded = False
_load_lock = threading.Lock()  # decode() and open_filter() can run from worker threads


def load_decoders() -> None:
    """Import every ``*_decoder`` module here; each registers its RawDecoder on import.

    Adding a RAW format is therefore one new file ``adapters/<name>_decoder.py``. The module
    scan runs once (idempotent, thread-safe); later calls return immediately.
    """
    global _loaded
    if _loaded:
        return
    with _load_lock:
        if _loaded:
            return
        _import_decoders()
        _loaded = True


def _import_decoders() -> None:
    # The explicit name is a fallback for frozen apps, where iter_modules may find nothing.
    names = {m.name for m in pkgutil.iter_modules(__path__) if m.name.endswith('_decoder')}
    for name in sorted(names | {'rawpy_decoder'}):
        try:
            importlib.import_module(f'{__name__}.{name}')
        except ImportError as exc:
            raise ValueError(f'No se pudo cargar el decodificador RAW «{name}»: {exc}') from exc
