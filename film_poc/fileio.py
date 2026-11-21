"""Atomic file replacement shared by every writer in the app."""
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path


@contextmanager
def atomic_path(destination: str | Path, suffix: str = '.tmp') -> Iterator[Path]:
    """Yield a temp path beside destination; os.replace it on success, always clean up."""
    destination = Path(destination)
    fd, name = tempfile.mkstemp(suffix=suffix, dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        yield temporary
        os.replace(temporary, destination)
    finally:
        with suppress(OSError):
            temporary.unlink()
