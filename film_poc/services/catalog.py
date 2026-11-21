"""Presentation metadata and reference thumbnails for the extensible look registry."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from ..adapters import reference_files
from ..core.render import LOOKS, apply_look, uint8
from .library import install


def metadata(name):
    install()
    look = LOOKS[name]
    return {'name': name, 'label': look.display_name, 'origin': look.origin, 'detail': look.detail}


def origins():
    install()
    return list(dict.fromkeys(metadata(name)['origin'] for name in LOOKS))


def filtered_names(origin='Todos los orígenes', query=''):
    install()
    query = query.casefold().strip()
    return [name for name in LOOKS if
            (origin == 'Todos los orígenes' or metadata(name)['origin'] == origin) and
            (not query or query in (name+' '+metadata(name)['origin']).casefold())]


@lru_cache(maxsize=1)
def reference_thumbnails():
    """Load precomputed sample cards; independent of any imported user image."""
    install()
    cards=reference_files.load_sample_cards(tuple(LOOKS))
    reference=reference_linear()
    return {name: cards[name] if name in cards else uint8(apply_look(reference,name))
            for name in tuple(LOOKS)}


def reference_linear():
    """Illustrative code-generated chart when no local reference is installed."""
    image=reference_files.load_local_reference()
    if image is None:
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
