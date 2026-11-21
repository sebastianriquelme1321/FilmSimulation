import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from film_poc.core import adjustments
from film_poc.core import render as engine
from film_poc.core.constants import REC709_LUMA_F32
from film_poc.core.looks.recipe import validate_recipe
from film_poc.core.preview import PreviewPipeline
from film_poc.services import library
from film_poc.services.export_bundle import export_raw_bundle
from film_poc.services.export_jpeg import export_jpeg

KEYS=('contrast','saturation','tint')


def sample():
    return np.random.default_rng(3).random((6,5,3),dtype=np.float32)


def test_neutral_is_bit_identical():
    x=sample()
    base=adjustments.apply_base(x,.3,12)
    np.testing.assert_array_equal(adjustments.apply_base(x,.3,12,0,0,0),base)
    name=next(iter(engine.LOOKS))
    a=engine.render_edit(x,name,.3,12,.7)
    b=engine.render_edit(x,name,.3,12,.7,contrast=0,saturation=0,tint=0)
    np.testing.assert_array_equal(a[1],b[1])


def test_contrast_direction_and_midgray_fixed():
    def up(v):
        return adjustments.apply_base(np.full((1,1,3),v,dtype=np.float32),contrast=60)[0,0,0]

    def down(v):
        return adjustments.apply_base(np.full((1,1,3),v,dtype=np.float32),contrast=-60)[0,0,0]

    assert up(.05)<.05 and up(.6)>.6 and up(.18)==pytest.approx(.18,abs=1e-6)
    assert down(.05)>.05 and down(.6)<.6
    ramp=np.linspace(0,1,50,dtype=np.float32)[None,:,None].repeat(3,2)
    for c in (-100,100):
        assert (np.diff(adjustments.apply_base(ramp,contrast=c)[0,:,0])>=0).all()


def test_saturation_direction():
    x=np.array([[[.5,.2,.1]]],dtype=np.float32)
    gray=adjustments.apply_base(x,saturation=-100)[0,0]
    assert np.ptp(gray)<1e-6
    assert gray[0]==pytest.approx(x[0,0]@REC709_LUMA_F32,abs=1e-6)
    def spread(s):
        return np.ptp(adjustments.apply_base(x,saturation=s)[0,0])

    assert spread(-50)<spread(0)<spread(50)


def test_tint_moves_green_magenta_preserving_luma():
    x=np.full((1,1,3),.3,dtype=np.float32)
    mag=adjustments.apply_base(x,tint=70)[0,0]
    grn=adjustments.apply_base(x,tint=-70)[0,0]
    assert mag[1]<mag[0] and mag[1]<mag[2]
    assert grn[1]>grn[0] and grn[1]>grn[2]
    for out in (mag,grn):
        assert out@REC709_LUMA_F32==pytest.approx(.3,abs=1e-5)


@pytest.mark.parametrize('key',KEYS)
def test_range_validation(key):
    adjustments.validate(**{key:100})
    adjustments.validate(**{key:-100})
    for bad in (101,-100.5,float('nan'),True):
        with pytest.raises(ValueError):
            adjustments.validate(**{key:bad})
    with pytest.raises(ValueError,match='contraste'):
        adjustments.validate(**{key:101})
    with pytest.raises(ValueError):
        adjustments.apply_base(sample(),**{key:200})
    with pytest.raises(ValueError):
        engine.render_edit(sample(),next(iter(engine.LOOKS)),**{key:200})


def test_edit_settings_include_new_keys():
    _,values=engine.edit_settings(next(iter(engine.LOOKS)),contrast=5)
    assert values['contrast']==5 and values['saturation']==0 and values['tint']==0


def _recipe(name,**extra):
    return {'version':1,'name':'Extra','base_look':name,'strength':.8,**extra}


def test_recipe_round_trip_and_legacy(tmp_path):
    name=next(iter(engine.LOOKS))
    x=sample()*.5
    registry=dict(engine.LOOKS)
    for extra in ({},{'contrast':30,'saturation':-20,'tint':15}):
        path=tmp_path/'r.json'
        path.write_text(json.dumps(_recipe(name,**extra)))
        key=library.import_profile(path,registry)
        engine.LOOKS[key]=registry[key]
        try:
            direct=engine.render_edit(x,name,intensity=.8,**extra)[1]
            np.testing.assert_allclose(engine.render_edit(x,key)[1],direct,atol=1e-7)
        finally:
            engine.LOOKS.pop(key)
        registry.pop(key,None)
    for bad in ({'contrast':101},{'tint':'x'},{'saturation':-101}):
        with pytest.raises(ValueError):
            validate_recipe(_recipe(name,**bad),engine.LOOKS)


def test_preview_cache_invalidates_on_new_knobs():
    x=sample()*.5
    name=next(iter(engine.LOOKS))
    pipe=PreviewPipeline()
    base,_=pipe.render(x,name)
    for key in KEYS:
        changed,_=pipe.render(x,name,**{key:60})
        assert not np.array_equal(changed,base),key
        pipe.render(x,name)
    _,after=pipe.render(x,name,contrast=40,saturation=-30,tint=20)
    expected=engine.uint8(engine.render_edit(x,name,contrast=40,saturation=-30,tint=20)[1])
    np.testing.assert_array_equal(after,expected)
    assert pipe.render(x,None,tint=10)[1] is None


def test_export_jpeg_matches_preview_with_new_knobs(tmp_path,monkeypatch):
    x=np.random.default_rng(4).random((300,7,3),dtype=np.float32)*.5
    name=next(iter(engine.LOOKS))
    expected=engine.uint8(engine.render_edit(x,name,contrast=25,saturation=40,tint=-30)[1])
    captured=[]
    original=Image.fromarray

    def capture(array):
        captured.append(array.copy())
        return original(array)
    monkeypatch.setattr(Image,'fromarray',capture)
    export_jpeg(x,name,tmp_path/'e.jpg',contrast=25,saturation=40,tint=-30)
    np.testing.assert_array_equal(captured[0],expected)


def test_export_bundle_writes_keys(tmp_path):
    src=tmp_path/'s.arw'
    src.write_bytes(b'raw')
    out=tmp_path/'b.zip'
    name=next(iter(engine.LOOKS))
    export_raw_bundle(src,name,out,contrast=10,saturation=-20,tint=30)
    with zipfile.ZipFile(out) as archive:
        recipe=json.loads(archive.read('edit.recipe.json'))
    assert (recipe['contrast'],recipe['saturation'],recipe['tint'])==(10,-20,30)
    validate_recipe(recipe,engine.LOOKS)
