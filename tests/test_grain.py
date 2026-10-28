import numpy as np
from film_poc.grain import apply_grain


def test_disabled_preserves_pixels_and_enabled_is_monochromatic():
    image=np.full((80,100,3),.5,dtype=np.float32)
    assert apply_grain(image) is image
    out=apply_grain(image,'Suave')
    assert out.std()>.005
    np.testing.assert_array_equal(out[...,0],out[...,1])
    np.testing.assert_array_equal(image,np.full_like(image,.5))
    assert apply_grain(image,'Fuerte').std()>out.std()*2


def test_grain_matches_export_strips_and_preview_coordinates():
    image=np.full((301,100,3),.3,dtype=np.float32)
    full=apply_grain(image,'Fuerte')
    strips=np.concatenate([apply_grain(image[:256],'Fuerte'),apply_grain(image[256:],'Fuerte',origin_y=256)])
    np.testing.assert_array_equal(full,strips)
    np.testing.assert_array_equal(full[::3,::3],apply_grain(image[::3,::3],'Fuerte',step=3))
    assert np.isfinite(full).all() and full.min()>=0 and full.max()<=1


def test_grain_is_in_exported_jpeg(tmp_path):
    from PIL import Image
    from film_poc.engine import export_jpeg,LOOKS
    source=np.full((70,90,3),.18,dtype=np.float32)
    plain=tmp_path/'plain.jpg'
    grain=tmp_path/'grain.jpg'
    export_jpeg(source,next(iter(LOOKS)),plain)
    export_jpeg(source,next(iter(LOOKS)),grain,grain='Fuerte')
    with Image.open(plain) as a,Image.open(grain) as b:
        assert np.asarray(b).std()>np.asarray(a).std()
        assert b.size==a.size and b.info['icc_profile']
