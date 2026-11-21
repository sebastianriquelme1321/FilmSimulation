"""User LUT/recipe files: .cube and HaldCLUT parsing, and the on-disk library entries."""
import hashlib
import json
import shutil
import struct
import zlib
from pathlib import Path
from typing import NamedTuple

import numpy as np

from ..core import tables
from .hald_loader import load_hald
from .storage import atomic_path, library_dir

MAX_BYTES = 16*1024*1024


def read_cube(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parse a 3D .cube file into (cube, domain_min, domain_max)."""
    size = None
    rows = []
    low = np.zeros(3)
    high = np.ones(3)
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        key = parts[0]
        if key == 'TITLE':
            continue
        if key == 'LUT_1D_SIZE':
            raise ValueError('Solo se admiten LUT 3D; este archivo contiene una LUT 1D.')
        if key == 'LUT_3D_SIZE':
            if size is not None or len(parts) != 2:
                raise ValueError('Cabecera LUT_3D_SIZE inválida.')
            size = int(parts[1])
            if not 2 <= size <= 65:
                raise ValueError('La LUT debe tener entre 2 y 65 puntos por eje.')
        elif key in ('DOMAIN_MIN', 'DOMAIN_MAX'):
            values = np.array([float(x) for x in parts[1:]])
            if values.shape != (3,):
                raise ValueError('Dominio de LUT inválido.')
            if key == 'DOMAIN_MIN':
                low = values
            else:
                high = values
        else:
            if size is None or len(parts) != 3 or len(rows) >= size**3:
                raise ValueError('La LUT tiene datos o un número de filas inválidos.')
            rows.append([float(x) for x in parts])
    if size is None or len(rows) != size**3 or not np.all(high > low):
        raise ValueError('LUT incompleta o dominio inválido.')
    cube = np.asarray(rows, dtype=np.float32).reshape(size, size, size, 3).transpose(2, 1, 0, 3)
    if not all(np.isfinite(x).all() for x in (cube, low, high)):
        raise ValueError('La LUT contiene valores no finitos.')
    return cube, low, high


def read_table(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read a .cube or HaldCLUT .png into (cube, domain_min, domain_max)."""
    if path.suffix.lower() == '.cube':
        return read_cube(path)
    header = path.read_bytes()[:29]
    if header[:8] != b'\x89PNG\r\n\x1a\n' or len(header) < 29:
        raise ValueError('PNG inválido.')
    width, height = struct.unpack('>II', header[16:24])
    if width != height or not 8 <= width <= 512:
        raise ValueError('Se admiten HaldCLUT cuadrados de nivel 2 a 8, no fotografías PNG.')
    try:
        return load_hald(path), np.zeros(3), np.ones(3)
    except (zlib.error, IndexError, struct.error, EOFError) as exc:
        raise ValueError('El PNG está dañado o truncado.') from exc


def register() -> None:
    """Hand the user-LUT table loader to the core."""
    tables.register_loader('user-lut', lambda path: read_table(Path(path)))


class Source(NamedTuple):
    digest: str
    suffix: str
    recipe: dict | None  # parsed JSON for recipes (not yet validated), else None


def read_source(path: Path) -> Source:
    """Check an importable file (size, type) and parse it; LUT tables are fully validated."""
    if path.suffix.lower() not in ('.cube', '.png', '.json') or path.stat().st_size > MAX_BYTES:
        raise ValueError('Importa una LUT .cube, HaldCLUT .png o receta .json de hasta 16 MB.')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    suffix = path.suffix.lower()
    if suffix == '.json':
        return Source(digest, suffix, json.loads(path.read_text(encoding='utf-8')))
    read_table(path)  # Validate before copying into the library.
    return Source(digest, suffix, None)


def store(path: Path, digest: str, entry: dict) -> None:
    """Copy a LUT (not recipes) into the library and write its entry file atomically."""
    root = library_dir()
    root.mkdir(parents=True, exist_ok=True)
    if entry['backend'] == 'user-lut':
        shutil.copyfile(path, root/entry['file'])
    with atomic_path(root/(digest+'.entry.json')) as temporary:
        temporary.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding='utf-8')


def read_entries() -> tuple[list[tuple[str, dict]], list[str]]:
    """Return ([(entry file name, entry)], names of unreadable entry files)."""
    entries, warnings = [], []
    for path in sorted(library_dir().glob('*.entry.json')):
        try:
            entry = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(entry, dict):
                raise ValueError('Entrada inválida')
            entries.append((path.name, entry))
        except (OSError, ValueError):
            warnings.append(path.name)
    return entries, warnings


def lut_exists(file: str) -> bool:
    return (library_dir()/file).is_file()


def bundle_files(lut_path: str | Path) -> list[Path]:
    """The LUT and its library entry, so a RAW archive can restore the look."""
    lut = Path(lut_path)
    entry = library_dir() / (lut.stem + '.entry.json')
    if not entry.is_file():
        raise ValueError('Falta la información local de la LUT para conservar la receta.')
    return [lut, entry]
