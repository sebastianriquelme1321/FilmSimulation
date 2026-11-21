"""Imported recipes: a base look plus exposure, warmth and intensity."""
from .base import registry


class RecipeBackend:
    def apply(self, linear, look):
        from ..engine import render_edit  # engine imports this package
        recipe = look['recipe']
        return render_edit(linear, recipe['base_look'], recipe.get('exposure_ev', 0),
                           recipe.get('temperature', 0), recipe.get('strength', 1.0))[1]


registry.add_backend('recipe', RecipeBackend())
