from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from film_poc.engine import LOOKS, apply_look, display_rgb, export_jpeg, decode


def test_transfer():
    np.testing.assert_allclose(display_rgb(np.array([0, .0031308, 1])), [0, .040449936, 1], atol=1e-6)


def test_looks_are_finite_distinct_and_do_not_mutate():
    rng = np.random.default_rng(42)
    source = rng.random((48, 64, 3), dtype=np.float32)
    original = source.copy()
    results = [apply_look(source, name) for name in LOOKS]
    np.testing.assert_array_equal(source, original)
    for rgb in results:
        assert rgb.shape == source.shape
        assert np.isfinite(rgb).all() and rgb.min() >= 0 and rgb.max() <= 1
    assert not np.allclose(results[0], results[1])


def test_jpeg_full_size_and_icc(tmp_path):
    source = np.full((513, 23, 3), .18, dtype=np.float32)
    path = tmp_path / 'result.jpg'
    export_jpeg(source, next(iter(LOOKS)), path)
    with Image.open(path) as image:
        assert image.size == (23, 513)
        assert image.format == 'JPEG'
        assert image.info['icc_profile']
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_input():
    with pytest.raises(ValueError):
        decode(Path('sample.dng'))
    with pytest.raises(Exception):
        decode(Path('missing.arw'))
