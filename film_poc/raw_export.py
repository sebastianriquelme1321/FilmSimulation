"""Non-destructive archive: untouched original ARW plus FilmSimulation settings."""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import zipfile
from .engine import LOOKS, PIPELINE_VERSION, edit_settings
from .grain import GRAIN
from .user_library import library_dir, validate_recipe


def export_raw_bundle(source, name, destination, grain='Desactivado', **adjustments):
    source,destination=Path(source),Path(destination)
    if source.suffix.lower()!='.arw' or not source.is_file():
        raise ValueError('Selecciona un archivo Sony ARW original existente.')
    if destination.suffix.lower()!='.zip':
        raise ValueError('RAW original + ajustes se guarda como archivo .zip.')
    if grain not in GRAIN: raise ValueError('Grano no compatible.')
    base,settings=edit_settings(name,**adjustments)
    recipe={'version':1,'name':LOOKS[name]['display_name']+' · edición',
            'base_look':base,'input_space':'sRGB','grain':grain,
            'strength':settings['intensity'],'exposure_ev':settings['exposure_ev'],
            'temperature':settings['temperature']}
    validate_recipe(recipe,LOOKS)
    fd,temporary=tempfile.mkstemp(suffix='.zip',dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            digest=hashlib.sha256()
            info=zipfile.ZipInfo('original/'+source.name)
            info.compress_type=zipfile.ZIP_STORED
            with source.open('rb') as original, archive.open(info,'w',force_zip64=True) as target:
                while block:=original.read(1024*1024):
                    digest.update(block)
                    target.write(block)
            profile=LOOKS[base]
            if profile.get('backend')=='user-lut':
                lut=Path(profile['path'])
                entry=library_dir()/(lut.stem+'.entry.json')
                if not entry.is_file():
                    raise ValueError('Falta la información local de la LUT para conservar la receta.')
                archive.write(lut,'library/'+lut.name)
                archive.write(entry,'library/'+entry.name)
            archive.writestr('edit.recipe.json',json.dumps(recipe,ensure_ascii=False,indent=2))
            archive.writestr('export-info.json',json.dumps({
                'format':'FilmSimulation original RAW archive','version':1,
                'pipeline':PIPELINE_VERSION,'original_sha256':digest.hexdigest(),
                'original_file':'original/'+source.name,
                'raw_modified':False,'temperature_unit':'relative RGB correction, not Kelvin',
                'input_space':'sRGB'},indent=2))
            archive.writestr('LEEME.txt',
                'El ARW es una copia intacta del original, con sus metadatos originales.\n'
                'La simulación NO está incorporada en los datos RAW.\n'
                'Importa el ARW y edit.recipe.json en FilmSimulation para recuperar los ajustes.\n'
                'Si hay una carpeta library, copia su contenido en la biblioteca local de FilmSimulation y reinicia.\n'
                'Otros reveladores no interpretan automáticamente esta receta.\n')
        os.replace(temporary,destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
