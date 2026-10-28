"""Local-only community LUT and recipe library. Never executes imported content."""
from pathlib import Path
from functools import lru_cache
import hashlib
import json
import os
import re
import shutil
import sys
import struct
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from .hald_loader import load_hald

MAX_BYTES=16*1024*1024


def library_dir():
    if os.environ.get('FILM_POC_USER_DIR'):
        return Path(os.environ['FILM_POC_USER_DIR'])
    if sys.platform=='darwin':
        return Path.home()/'Library'/'Application Support'/'FilmPOC'
    if sys.platform=='win32':
        return Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'FilmPOC'
    return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'FilmPOC'


def read_cube(path):
    size=None
    rows=[]
    low=np.zeros(3)
    high=np.ones(3)
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line=raw.split('#',1)[0].strip()
        if not line:
            continue
        parts=line.split()
        key=parts[0]
        if key=='TITLE':
            continue
        if key=='LUT_1D_SIZE':
            raise ValueError('Solo se admiten LUT 3D; este archivo contiene una LUT 1D.')
        if key=='LUT_3D_SIZE':
            if size is not None or len(parts)!=2:
                raise ValueError('Cabecera LUT_3D_SIZE inválida.')
            size=int(parts[1])
            if not 2<=size<=65:
                raise ValueError('La LUT debe tener entre 2 y 65 puntos por eje.')
        elif key in ('DOMAIN_MIN','DOMAIN_MAX'):
            values=np.array([float(x) for x in parts[1:]])
            if values.shape!=(3,):
                raise ValueError('Dominio de LUT inválido.')
            if key=='DOMAIN_MIN': low=values
            else: high=values
        else:
            if size is None or len(parts)!=3 or len(rows)>=size**3:
                raise ValueError('La LUT tiene datos o un número de filas inválidos.')
            rows.append([float(x) for x in parts])
    if size is None or len(rows)!=size**3 or not np.all(high>low):
        raise ValueError('LUT incompleta o dominio inválido.')
    cube=np.asarray(rows,dtype=np.float32).reshape(size,size,size,3).transpose(2,1,0,3)
    if not all(np.isfinite(x).all() for x in (cube,low,high)):
        raise ValueError('La LUT contiene valores no finitos.')
    return cube,low,high


def read_table(path):
    if path.suffix.lower()=='.cube':
        return read_cube(path)
    header=path.read_bytes()[:29]
    if header[:8]!=b'\x89PNG\r\n\x1a\n' or len(header)<29:
        raise ValueError('PNG inválido.')
    width,height=struct.unpack('>II',header[16:24])
    if width!=height or not 8<=width<=512:
        raise ValueError('Se admiten HaldCLUT cuadrados de nivel 2 a 8, no fotografías PNG.')
    return load_hald(path),np.zeros(3),np.ones(3)


@lru_cache(maxsize=20)
def _table(path):
    cube,low,high=read_table(Path(path))
    axis=np.linspace(0,1,len(cube))
    return RegularGridInterpolator((axis,axis,axis),cube,bounds_error=True),low,high


def apply(rgb,profile):
    table,low,high=_table(profile['path'])
    coordinates=np.clip((rgb-low)/(high-low),0,1)
    return np.clip(table(coordinates.reshape(-1,3)).reshape(rgb.shape),0,1).astype(np.float32)


def validate_recipe(data,registry):
    allowed={'version','name','author','source','license','base_look','strength','grain','input_space'}
    if not isinstance(data,dict) or set(data)-allowed or data.get('version')!=1:
        raise ValueError('Receta no compatible. Usa el formato JSON de Film POC versión 1.')
    if data.get('input_space','sRGB')!='sRGB':
        raise ValueError('Este flujo admite únicamente recetas de entrada sRGB.')
    for field in ('name','author','source','license','base_look'):
        if field in data and (not isinstance(data[field],str) or len(data[field])>500):
            raise ValueError('Metadatos de receta inválidos.')
    base=data.get('base_look')
    if base not in registry or registry[base].get('backend')=='recipe':
        raise ValueError('La simulación base no está instalada o es otra receta.')
    strength=data.get('strength',1.0)
    if isinstance(strength,bool) or not isinstance(strength,(float,int)) or not 0<=strength<=1:
        raise ValueError('La intensidad debe estar entre 0 y 1.')
    if data.get('grain','Desactivado') not in ('Desactivado','Suave','Fuerte'):
        raise ValueError('Grano de receta inválido.')
    if not isinstance(data.get('name'),str) or not data['name'].strip():
        raise ValueError('La receta necesita un nombre.')
    return data


def _profile(entry,root):
    details=' · '.join(x for x in (entry.get('author'),entry.get('license'),'Entrada sRGB · importado localmente') if x)
    p={'display_name':entry['name'],'origin':'Comunidad / local','detail':details,
       'backend':entry['backend'],'source':entry.get('source','')}
    if p['backend']=='recipe': p['recipe']=entry['recipe']
    else: p['path']=str(root/entry['file'])
    return p


def import_profile(path,registry):
    path=Path(path)
    if path.suffix.lower() not in ('.cube','.png','.json') or path.stat().st_size>MAX_BYTES:
        raise ValueError('Importa una LUT .cube, HaldCLUT .png o receta .json de hasta 16 MB.')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    root=library_dir()
    label=path.stem[:70]
    entry={'name':label,'backend':'user-lut','file':digest+path.suffix.lower(),
           'source':'','license':'No declarada; uso local'}
    if path.suffix.lower()=='.json':
        recipe=validate_recipe(json.loads(path.read_text(encoding='utf-8')),registry)
        entry.update({key:recipe.get(key,'') for key in ('name','author','source','license')})
        entry.update(backend='recipe',recipe=recipe)
    else:
        read_table(path)  # Validate before copying into the library.
    key=f"{entry['name']} · local {digest[:8]}"
    root.mkdir(parents=True,exist_ok=True)
    if entry['backend']=='user-lut': shutil.copyfile(path,root/entry['file'])
    temporary=root/(digest+'.tmp')
    temporary.write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(root/(digest+'.entry.json'))
    registry[key]=_profile(entry,root)
    return key


def load_library(registry):
    warnings=[]
    root=library_dir()
    files=sorted(root.glob('*.entry.json'))
    # LUTs first, then recipes referring to them.
    entries=[]
    for path in files:
        try:
            entry=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(entry,dict): raise ValueError('Entrada inválida')
            entries.append((path,entry))
        except (OSError,ValueError): warnings.append(path.name)
    for path,entry in sorted(entries,key=lambda pair:pair[1].get('backend')=='recipe'):
        try:
            if entry['backend']=='recipe': validate_recipe(entry['recipe'],registry)
            elif entry['backend']=='user-lut':
                if Path(entry['file']).name!=entry['file']: raise ValueError('Ruta inválida')
                if not (root/entry['file']).is_file(): raise ValueError('LUT no encontrada')
            else: raise ValueError('Tipo desconocido')
            key=f"{entry['name']} · local {path.name[:8]}"
            registry[key]=_profile(entry,root)
        except (KeyError,TypeError,OSError,ValueError): warnings.append(path.name)
    return warnings
