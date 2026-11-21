"""Local UI preferences, separate from imported recipes and project files."""
from collections.abc import Collection
from pathlib import Path

from ..adapters import storage


def load_theme(themes: Collection[str], default: str) -> str:
    """Return the saved theme name, or the default if missing or unknown."""
    theme = storage.load_theme_name()
    return theme if theme in themes else default


def save_theme(theme: str, themes: Collection[str]) -> None:
    """Persist the theme name atomically."""
    if theme not in themes:
        raise ValueError('Tema desconocido')
    storage.save_theme_name(theme)


def load_export_dir() -> Path | None:
    """Folder of the last export, or None if never set or no longer available."""
    return storage.load_export_dir()


def save_export_dir(folder: str | Path) -> None:
    """Remember the folder of the last export."""
    storage.save_export_dir(folder)


def load_surround(surrounds: Collection[str], default: str) -> str:
    """Return the saved viewer backdrop, or the default if missing or unknown."""
    surround = storage.load_surround_name()
    return surround if surround in surrounds else default


def save_surround(surround: str, surrounds: Collection[str]) -> None:
    """Persist the viewer backdrop name atomically."""
    if surround not in surrounds:
        raise ValueError('Fondo desconocido')
    storage.save_surround_name(surround)
