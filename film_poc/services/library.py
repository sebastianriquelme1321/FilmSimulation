"""Use cases around the look registry: startup, importing LUTs/recipes, saving recipes.

Local-only community library; imported content is validated and never executed.
"""
import json
import threading
from pathlib import Path

from ..adapters import darktable_files, film_stock_files, lut_files
from ..adapters.storage import atomic_path, library_dir
from ..core.looks.recipe import validate_recipe
from ..core.render import LOOKS

_installed = False
_install_lock = threading.Lock()  # install() can run from worker threads


def install() -> None:
    """Wire adapters into the core and register the bundled film stocks (idempotent)."""
    global _installed
    if _installed:
        return
    with _install_lock:
        if _installed:
            return
        darktable_files.register()
        lut_files.register()
        film_stock_files.register(LOOKS)
        _installed = True


def _key(name: str, digest: str) -> str:
    """Registry key of a user look: its name plus the short content digest."""
    return f'{name} · local {digest[:8]}'


def startup() -> list[str]:
    """install() and register the user's library; return entry files that failed to load."""
    install()
    return load_library(LOOKS)


def _profile(entry: dict, root: Path) -> dict:
    parts = (entry.get('author'), entry.get('license'), 'Entrada sRGB · importado localmente')
    details = ' · '.join(x for x in parts if x)
    p = {'display_name': entry['name'], 'origin': 'Comunidad / local', 'detail': details,
         'backend': entry['backend'], 'source': entry.get('source', '')}
    if p['backend'] == 'recipe':
        p['recipe'] = entry['recipe']
    else:
        p['path'] = str(root/entry['file'])
    return p


def import_profile(path: str | Path, registry: dict = LOOKS) -> str:
    """Validate and copy a LUT/recipe into the library; register it and return its key."""
    install()
    path = Path(path)
    source = lut_files.read_source(path)
    label = path.stem[:70]
    entry = {'name': label, 'backend': 'user-lut', 'file': source.digest+source.suffix,
             'source': '', 'license': 'No declarada; uso local'}
    if source.recipe is not None:
        recipe = validate_recipe(source.recipe, registry)
        entry.update({key: recipe.get(key, '') for key in ('name', 'author', 'source', 'license')})
        entry.update(backend='recipe', recipe=recipe)
    key = _key(entry['name'], source.digest)
    lut_files.store(path, source.digest, entry)
    registry[key] = _profile(entry, library_dir())
    return key


def load_library(registry: dict = LOOKS) -> list[str]:
    """Register all valid library entries; return file names that failed to load."""
    install()
    entries, warnings = lut_files.read_entries()
    root = library_dir()
    # LUTs first, then recipes referring to them.
    for name, entry in sorted(entries, key=lambda pair: pair[1].get('backend') == 'recipe'):
        try:
            if entry['backend'] == 'recipe':
                validate_recipe(entry['recipe'], registry)
            elif entry['backend'] == 'user-lut':
                if Path(entry['file']).name != entry['file']:
                    raise ValueError('Ruta inválida')
                if not lut_files.lut_exists(entry['file']):
                    raise ValueError('LUT no encontrada')
            else:
                raise ValueError('Tipo desconocido')
            key = _key(entry['name'], name)  # name is '<digest>.entry.json'
            registry[key] = _profile(entry, root)
        except (KeyError, TypeError, OSError, ValueError):
            warnings.append(name)
    return warnings


def save_recipe(data: dict, path: str | Path) -> None:
    """Validate a recipe against the registry and write it as a shareable JSON file."""
    install()
    validate_recipe(data, LOOKS)
    with atomic_path(path) as temporary:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
