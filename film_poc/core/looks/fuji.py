"""fujiLUT-derived profiles (tone curve, matrix, HSL) and local B/N filter variants."""
from copy import deepcopy

import numpy as np

from ..profile_transforms import apply_base_saturation, apply_film_simulation
from ..profiles import PROFILES
from .base import Look, display_rgb, registry

_DETAIL = 'Perfil adaptado de fujiLUT · MIT · aproximación'
_FILTERS = (('Ye', [.30, .60, .10]), ('R', [.60, .32, .08]), ('G', [.18, .74, .08]))


class FujiBackend:
    def apply(self, linear, look):
        x = display_rgb(linear).astype(np.float64)
        rgb = apply_film_simulation(x.reshape(-1, 3), look.params)
        # Upstream Sepia has saturation=0, which erases its warm matrix/tints.
        if look.display_name != 'Sepia':
            rgb = apply_base_saturation(rgb, look.params['base_saturation'])
        return np.clip(rgb.reshape(x.shape), 0, 1).astype(np.float32)


def _look(profile, origin='fujiLUT', detail=_DETAIL):
    params = {k: v for k, v in profile.items() if k not in ('display_name', 'backend')}
    return Look(profile['display_name'], profile.get('backend'), origin, detail, params)


registry.add_backend('fuji', FujiBackend())
registry['Classic Chrome (aproximación)'] = _look(PROFILES['Classic Chrome'])
registry['Classic Negative (aproximación)'] = _look(PROFILES['Classic Neg'])
for _key, _profile in PROFILES.items():
    if _key not in ('Classic Chrome', 'Classic Neg'):
        registry[f"{_profile['display_name']} (aproximación)"] = _look(_profile)
# Local approximations of the six monochrome color-filter variants. Neutral
# inputs remain neutral; only the RGB contribution to monochrome changes.
for _key, _label in (('Acros', 'ACROS'), ('Mono', 'Monochrome')):
    for _filter, _weights in _FILTERS:
        _variant = deepcopy(PROFILES[_key])
        _variant['display_name'] = f'{_label} + {_filter}'
        _variant['color_matrix'] = [list(_weights) for _ in range(3)]
        registry[f'{_label} + {_filter} (aproximación)'] = _look(
            _variant, 'Personalizadas',
            'Variante local de filtro B/N sobre fujiLUT · aproximación')
