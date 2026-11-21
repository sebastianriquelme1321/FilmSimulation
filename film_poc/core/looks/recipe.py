"""Imported recipes: a base look plus exposure, warmth and intensity.

The backend is registered by ``core/render.py`` (a recipe renders through ``render_edit``).
"""
from ..adjustments import validate
from ..grain import GRAIN

_ALLOWED = {'version', 'name', 'author', 'source', 'license', 'base_look', 'strength', 'grain',
            'input_space', 'exposure_ev', 'temperature'}


class RecipeBackend:
    def __init__(self, render_edit):
        self._render_edit = render_edit

    def apply(self, linear, look):
        recipe = look['recipe']
        return self._render_edit(linear, recipe['base_look'], recipe.get('exposure_ev', 0),
                                 recipe.get('temperature', 0), recipe.get('strength', 1.0))[1]


def validate_recipe(data: dict, registry: dict) -> dict:
    """Return data if it is a valid version-1 recipe against registry, else raise ValueError."""
    if not isinstance(data, dict) or set(data) - _ALLOWED or data.get('version') != 1:
        raise ValueError('Receta no compatible. Usa el formato JSON de Film POC versión 1.')
    if data.get('input_space', 'sRGB') != 'sRGB':
        raise ValueError('Este flujo admite únicamente recetas de entrada sRGB.')
    for field in ('name', 'author', 'source', 'license', 'base_look'):
        if field in data and (not isinstance(data[field], str) or len(data[field]) > 500):
            raise ValueError('Metadatos de receta inválidos.')
    base = data.get('base_look')
    if base not in registry or registry[base].get('backend') == 'recipe':
        raise ValueError('La simulación base no está instalada o es otra receta.')
    strength = data.get('strength', 1.0)
    if (isinstance(strength, bool) or not isinstance(strength, (float, int))
            or not 0 <= strength <= 1):
        raise ValueError('La intensidad debe estar entre 0 y 1.')
    if data.get('grain', 'Desactivado') not in GRAIN:
        raise ValueError('Grano de receta inválido.')
    if not isinstance(data.get('name'), str) or not data['name'].strip():
        raise ValueError('La receta necesita un nombre.')
    validate(data.get('exposure_ev', 0), data.get('temperature', 0), strength)
    return data
