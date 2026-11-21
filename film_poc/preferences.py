"""Local UI preferences, separate from imported recipes and project files."""
import json

from .fileio import atomic_path
from .theme import DEFAULT_THEME, THEMES
from .user_library import library_dir


def load_theme() -> str:
    """Return the saved theme name, or the default if missing or invalid."""
    try:
        data = json.loads((library_dir() / 'appearance.json').read_text(encoding='utf-8'))
        theme = data.get('theme') if isinstance(data, dict) else None
        return theme if theme in THEMES else DEFAULT_THEME
    except (OSError, ValueError, TypeError):
        return DEFAULT_THEME


def save_theme(theme: str) -> None:
    """Persist the theme name atomically."""
    if theme not in THEMES:
        raise ValueError('Tema desconocido')
    root = library_dir()
    root.mkdir(parents=True, exist_ok=True)
    with atomic_path(root / 'appearance.json') as temporary:
        temporary.write_text(json.dumps({'theme': theme}), encoding='utf-8')
