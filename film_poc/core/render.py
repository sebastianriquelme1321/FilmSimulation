"""Render pipeline: base adjustments, look, intensity mix. Pure arrays in, arrays out."""
import re
from typing import NamedTuple

import numpy as np

from . import adjustments
from .looks import registry
from .looks.base import display_rgb
from .looks.recipe import RecipeBackend

LOOKS = registry
PIPELINE_VERSION = 'v4.1-base-adjustments-mix'


def look_slug(name: str) -> str:
    """Return a filesystem-safe slug for the look's display name."""
    profile = LOOKS[name]
    return re.sub(r'[^a-z0-9]+', '_', profile['display_name'].lower()).strip('_')


def render_base(linear: np.ndarray) -> np.ndarray:
    """Display-encode linear sRGB (the common base rendering)."""
    return display_rgb(linear)


def apply_look(linear: np.ndarray, name: str) -> np.ndarray:
    """Render linear sRGB through the named look; returns display-encoded float32."""
    look = LOOKS[name]
    return LOOKS.backend(look).apply(linear, look)


class EditSettings(NamedTuple):
    base_name: str
    values: dict


def edit_settings(name: str, exposure_ev: float | None = None, temperature: float | None = None,
                  intensity: float | None = None) -> EditSettings:
    """Resolve and validate edit values (recipe defaults fill in omitted ones)."""
    profile = LOOKS[name]
    recipe = profile.get('recipe', {}) if profile.get('backend') == 'recipe' else {}
    values = {'exposure_ev': recipe.get('exposure_ev', 0) if exposure_ev is None else exposure_ev,
              'temperature': recipe.get('temperature', 0) if temperature is None else temperature,
              'intensity': recipe.get('strength', 1) if intensity is None else intensity}
    adjustments.validate(**values)
    return EditSettings(recipe.get('base_look', name), values)


def render_edit(linear: np.ndarray, name: str, exposure_ev: float | None = None,
                temperature: float | None = None,
                intensity: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return adjusted base and mixed look; both display-encoded sRGB, no grain."""
    base_name, settings = edit_settings(name, exposure_ev, temperature, intensity)
    corrected = adjustments.apply_base(linear, settings['exposure_ev'], settings['temperature'])
    before = render_base(corrected)
    amount = settings['intensity']
    if amount == 0:
        return before, before.copy()
    after = apply_look(corrected, base_name)
    mixed = before*(1-amount) + after*amount
    return before, np.clip(mixed, 0, 1).astype(np.float32)


def uint8(rgb: np.ndarray) -> np.ndarray:
    """Convert display-encoded [0, 1] floats to rounded uint8."""
    return np.rint(np.clip(rgb, 0, 1)*255).astype(np.uint8)


# A recipe is a base look plus edits, so it renders through render_edit itself.
LOOKS.add_backend('recipe', RecipeBackend(render_edit))
