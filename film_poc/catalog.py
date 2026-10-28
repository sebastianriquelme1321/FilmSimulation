"""Presentation metadata and thumbnails for the extensible look registry."""
import numpy as np
from pathlib import Path
from functools import lru_cache
import json
from PIL import Image,ImageDraw
from .engine import LOOKS, apply_look, uint8
from .film_stocks import STOCKS


def metadata(name):
    profile = LOOKS[name]
    if profile.get('backend') == 'darktable':
        origin = 'darktable'
        detail = 'Preset Lab adaptado de darktable · GPL · experimental'
    elif profile.get('backend') == 'film-stock':
        asset = STOCKS[profile['stock']]
        origin = 'spektrafilm / Film Lab' if 'spektrafilm' in asset['source'] else 'Pat David / HaldCLUT'
        detail = f"{asset['source']} · {asset['license']} · aproximación de película"
    elif ' + ' in profile['display_name']:
        origin = 'Personalizadas'
        detail = 'Variante local de filtro B/N sobre fujiLUT · aproximación'
    else:
        origin = 'fujiLUT'
        detail = 'Perfil adaptado de fujiLUT · MIT · aproximación'
    return {'name': name, 'label': profile['display_name'],
            'origin': profile.get('origin',origin), 'detail': profile.get('detail',detail)}


def origins():
    return list(dict.fromkeys(metadata(name)['origin'] for name in LOOKS))


def filtered_names(origin='Todos los orígenes', query=''):
    query = query.casefold().strip()
    return [name for name in LOOKS if
            (origin == 'Todos los orígenes' or metadata(name)['origin'] == origin) and
            (not query or query in (name+' '+metadata(name)['origin']).casefold())]


def thumbnails(linear):
    """Small versions of the user's current image, without output grain.

    Called in the import worker. No extra full-resolution frames are retained.
    """
    step = max(1, (max(linear.shape[:2])+239)//240)
    small = np.ascontiguousarray(linear[::step,::step])
    return {name: uint8(apply_look(small,name)) for name in LOOKS}


@lru_cache(maxsize=1)
def reference_thumbnails():
    """Load precomputed sample cards; independent of any imported user image."""
    folder=Path(__file__).parent/'assets'/'reference'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8')) if (folder/'manifest.json').exists() else {}
    reference=reference_linear()
    return {name: (np.asarray(Image.open(folder/manifest[name]).convert('RGB')).copy()
                   if name in manifest and (folder/manifest[name]).exists()
                   else uint8(apply_look(reference,name))) for name in tuple(LOOKS)}


def reference_linear():
    """Illustrative code-generated chart when no local reference is installed."""
    from .user_library import library_dir
    local=library_dir()/'reference.jpg'
    if local.exists():
        image=Image.open(local).convert('RGB')
        image.thumbnail((240,160))
    else:
        image=Image.new('RGB',(240,160),'#b5afa4')
        draw=ImageDraw.Draw(image)
        for y in range(160):
            shade=int(238-150*y/159)
            draw.line((0,y,240,y),fill=(shade,shade,shade))
        # Original still-life illustration with neutral and saturated surfaces.
        draw.polygon([(0,118),(240,103),(240,160),(0,160)],fill='#a17c59')
        draw.rounded_rectangle((25,60,80,130),10,fill='#416f9d')
        draw.ellipse((72,83,126,135),fill='#b94b3d')
        draw.ellipse((124,101,180,137),fill='#e2bd49')
        draw.rounded_rectangle((172,78,207,121),5,fill='#d8d1bf')
        draw.ellipse((180,29,202,92),fill='#427d50')
        draw.ellipse((156,44,193,70),fill='#56894c')
        draw.ellipse((193,42,225,72),fill='#6b9959')
    rgb=np.asarray(image).astype(np.float32)/255
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
