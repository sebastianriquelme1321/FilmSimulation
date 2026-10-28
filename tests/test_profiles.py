from copy import deepcopy
import numpy as np
from film_poc.engine import LOOKS, apply_look, render_base
from film_poc.profiles import PROFILES
from film_poc.profile_transforms import (_hue_weight, apply_film_simulation,
                                         apply_base_saturation)


def test_hue_weight_continuous_at_boundary_and_wrap():
    weights = _hue_weight(np.array([29.999, 30, 30.001]), 0, 30)
    assert np.max(np.abs(np.diff(weights))) < 1e-7
    np.testing.assert_allclose(_hue_weight(np.array([1, 359]), 0, 30),
                               [_hue_weight(np.array([1]), 0, 30)[0]] * 2)


def test_hue_range_order_does_not_change_result():
    profile = deepcopy(PROFILES['Classic Chrome'])
    reversed_profile = deepcopy(profile)
    reversed_profile['hsl_shifts'] = dict(reversed(list(profile['hsl_shifts'].items())))
    pixels = np.random.default_rng(4).random((1000, 3))
    np.testing.assert_allclose(apply_film_simulation(pixels, profile),
                               apply_film_simulation(pixels, reversed_profile), atol=1e-12)


def test_linear_adapter_and_strip_consistency():
    linear = np.random.default_rng(8).random((19, 23, 3), dtype=np.float32)
    for name, profile in LOOKS.items():
        if profile.get('backend'):
            continue
        expected = apply_film_simulation(render_base(linear).astype(np.float64).reshape(-1, 3), profile)
        if profile['display_name'] != 'Sepia':
            expected = apply_base_saturation(expected, profile['base_saturation'])
        expected = expected.reshape(linear.shape)
        np.testing.assert_allclose(apply_look(linear, name), expected, atol=1e-7)
        strips = np.concatenate([apply_look(linear[:7], name), apply_look(linear[7:], name)])
        np.testing.assert_array_equal(apply_look(linear, name), strips)
