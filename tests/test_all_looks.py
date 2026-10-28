import numpy as np
from film_poc.engine import LOOKS, apply_look, look_slug, export_jpeg
from PIL import Image


def test_all_looks_export_distinct_names_and_valid_images(tmp_path):
    source = np.random.default_rng(17).random((24,32,3),dtype=np.float32)
    slugs = [look_slug(name) for name in LOOKS]
    assert len(set(slugs)) == len(LOOKS) == 31
    for name in LOOKS:
        out = apply_look(source, name)
        assert out.shape == source.shape and np.isfinite(out).all()
        assert out.min() >= 0 and out.max() <= 1
        path = tmp_path / (look_slug(name)+'.jpg')
        export_jpeg(source, name, path)
        with Image.open(path) as image:
            assert image.size == (32,24) and image.info.get('icc_profile')


def test_monochrome_neutral_and_sepia_warm():
    source = np.full((2,3,3),.18,dtype=np.float32)
    for name in LOOKS:
        result = apply_look(source,name)
        if name.startswith(('ACROS','Monochrome')):
            # Lab D50 conversion of the darktable neutral has small rounding error.
            tolerance = 1e-4 if 'darktable' in name else 1e-6
            np.testing.assert_allclose(result[...,0],result[...,1],atol=tolerance)
            np.testing.assert_allclose(result[...,1],result[...,2],atol=tolerance)
        if name.startswith('Sepia'):
            assert np.all(result[...,0]>result[...,1])
            assert np.all(result[...,1]>result[...,2])
