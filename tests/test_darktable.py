import numpy as np
from film_poc.darktable_look import patches,mapping,to_lab,from_lab,direct,apply
from film_poc.darktable_look import PRESETS
import pytest


@pytest.mark.parametrize('preset',PRESETS)
def test_patch_interpolation_reproduces_upstream_targets(preset):
    source,target=patches(preset)
    assert source.shape == target.shape == (49,3)
    np.testing.assert_allclose(mapping(preset)(source),target,atol=1e-6)


def test_color_conversion_roundtrip():
    rgb=np.random.default_rng(2).random((100,3))
    np.testing.assert_allclose(from_lab(to_lab(rgb)),rgb,atol=1e-6)


@pytest.mark.parametrize('preset',PRESETS)
def test_lut_approximation_and_strips(preset):
    rgb=np.random.default_rng(3).random((30,40,3))
    result=apply(rgb,preset)
    error=np.abs(result-direct(rgb,preset))
    assert np.percentile(error,99) < .025
    assert error.max() < .08
    np.testing.assert_array_equal(result,np.concatenate([apply(rgb[:10],preset),apply(rgb[10:],preset)]))
