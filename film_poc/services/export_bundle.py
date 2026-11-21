"""Use case: non-destructive archive with the untouched original RAW plus the edit settings."""
import hashlib
import json
import zipfile
from pathlib import Path

from .. import adapters
from ..adapters import lut_files
from ..adapters.storage import atomic_path
from ..core import raw
from ..core.grain import GRAIN
from ..core.looks.recipe import validate_recipe
from ..core.render import LOOKS, PIPELINE_VERSION, edit_settings


def export_raw_bundle(source: str | Path, name: str, destination: str | Path,
                      grain: str = 'Desactivado', **adjustments: float) -> None:
    """Write a .zip with the untouched RAW, edit.recipe.json and export metadata."""
    source, destination = Path(source), Path(destination)
    adapters.load_decoders()
    if not raw.is_supported(source) or not source.is_file():
        raise ValueError('Selecciona un archivo Sony ARW original existente.')
    if destination.suffix.lower() != '.zip':
        raise ValueError('RAW original + ajustes se guarda como archivo .zip.')
    if grain not in GRAIN:
        raise ValueError('Grano no compatible.')
    base, settings = edit_settings(name, **adjustments)
    recipe = {'version': 1, 'name': LOOKS[name]['display_name'] + ' · edición',
              'base_look': base, 'input_space': 'sRGB', 'grain': grain,
              'strength': settings['intensity'], 'exposure_ev': settings['exposure_ev'],
              'temperature': settings['temperature']}
    validate_recipe(recipe, LOOKS)
    with atomic_path(destination, '.zip') as temporary:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            digest = hashlib.sha256()
            info = zipfile.ZipInfo('original/' + source.name)
            info.compress_type = zipfile.ZIP_STORED
            with source.open('rb') as original, archive.open(info, 'w', force_zip64=True) as target:
                while block := original.read(1024*1024):
                    digest.update(block)
                    target.write(block)
            profile = LOOKS[base]
            # Only imported LUTs live outside the app; they travel with the archive.
            files = lut_files.bundle_files(profile['path']) if profile.backend == 'user-lut' else []
            for file in files:
                archive.write(file, 'library/' + file.name)
            archive.writestr('edit.recipe.json', json.dumps(recipe, ensure_ascii=False, indent=2))
            archive.writestr('export-info.json', json.dumps({
                'format': 'FilmSimulation original RAW archive', 'version': 1,
                'pipeline': PIPELINE_VERSION, 'original_sha256': digest.hexdigest(),
                'original_file': 'original/' + source.name,
                'raw_modified': False, 'temperature_unit': 'relative RGB correction, not Kelvin',
                'input_space': 'sRGB'}, indent=2))
            archive.writestr('LEEME.txt',
                'El ARW es una copia intacta del original, con sus metadatos originales.\n'
                'La simulación NO está incorporada en los datos RAW.\n'
                'Importa el ARW y edit.recipe.json en FilmSimulation para recuperar los ajustes.\n'
                'Si hay una carpeta library, copia su contenido en la biblioteca local de '
                'FilmSimulation y reinicia.\n'
                'Otros reveladores no interpretan automáticamente esta receta.\n')
