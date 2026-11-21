"""Experimental Lab-patch presets adapted from darktable."""
import numpy as np

from .. import darktable_look
from .base import Look, display_rgb, registry


class DarktableBackend:
    def apply(self, linear, look):
        return darktable_look.apply(display_rgb(linear).astype(np.float64), look.params['preset'])


registry.add_backend('darktable', DarktableBackend())
for _preset, _label in darktable_look.PRESETS.items():
    registry[f'{_label} · darktable (experimental)'] = Look(
        f'{_label} darktable', 'darktable', 'darktable',
        'Preset Lab adaptado de darktable · GPL · experimental', {'preset': _preset})
