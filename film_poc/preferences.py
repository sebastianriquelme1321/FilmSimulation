"""Local UI preferences, separate from imported recipes and project files."""
import json
import os
import tempfile
from .user_library import library_dir
from .theme import THEMES,DEFAULT_THEME


def load_theme():
    try:
        data=json.loads((library_dir()/'appearance.json').read_text(encoding='utf-8'))
        theme=data.get('theme') if isinstance(data,dict) else None
        return theme if theme in THEMES else DEFAULT_THEME
    except (OSError,ValueError,TypeError):
        return DEFAULT_THEME


def save_theme(theme):
    if theme not in THEMES: raise ValueError('Tema desconocido')
    root=library_dir()
    temporary=None
    try:
        root.mkdir(parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(suffix='.tmp',dir=root)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump({'theme':theme},stream)
        os.replace(temporary,root/'appearance.json')
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)
