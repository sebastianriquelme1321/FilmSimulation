import numpy as np
from film_poc.engine import render_base, display_rgb, match_camera_tone


def test_neutral_ramp_retains_endpoints_and_is_monotonic():
    ramp = np.repeat(np.linspace(0, 1, 4096, dtype=np.float32)[:, None], 3, axis=1)
    out = render_base(ramp)
    np.testing.assert_allclose(out[0], 0, atol=1e-7)
    np.testing.assert_allclose(out[-1], 1, atol=1e-6)
    assert np.all(np.diff(out[:, 0]) >= -1e-7)
    np.testing.assert_allclose(out[:, 0], out[:, 1], atol=1e-6)
    np.testing.assert_array_equal(out, display_rgb(ramp))


def test_camera_reference_recovers_tones_without_modifying_input():
    from PIL import Image
    ramp = np.repeat(np.linspace(0, .4, 1000, dtype=np.float32)[None,:,None],3,axis=2)
    original = ramp.copy()
    desired = np.clip(ramp*2,0,1)
    ref = Image.fromarray(np.rint(display_rgb(desired)*255).astype(np.uint8))
    result = match_camera_tone(ramp,ref)
    np.testing.assert_array_equal(ramp,original)
    np.testing.assert_allclose(result[:,100:900], desired[:,100:900],atol=.006)
    assert np.isfinite(result).all()


def test_saturated_colors_finite_in_gamut_and_input_unchanged():
    pixels = np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,1,1],[.03,.06,.1]],dtype=np.float32)
    original = pixels.copy()
    out = render_base(pixels)
    np.testing.assert_array_equal(pixels, original)
    assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1
