from pathlib import Path
import hashlib
import json
import zipfile
import numpy as np
import pytest
from film_poc import adjustments, engine, user_library
from film_poc.raw_export import export_raw_bundle
from film_poc.grain import apply_grain


def test_exposure_temperature_and_input_preservation():
    source=np.full((3,4,3),.1,dtype=np.float32)
    copy=source.copy()
    np.testing.assert_allclose(adjustments.apply_base(source,1),source*2,atol=1e-7)
    warm=adjustments.apply_base(source,temperature=80)
    cool=adjustments.apply_base(source,temperature=-80)
    assert warm[0,0,0]>warm[0,0,2]
    assert cool[0,0,0]<cool[0,0,2]
    np.testing.assert_array_equal(source,copy)
    for values in ((float('nan'),0,1),(0,101,1),(0,0,2)):
        with pytest.raises(ValueError): adjustments.validate(*values)


def test_mix_endpoints_and_recipe_round_trip(tmp_path):
    source=np.random.default_rng(8).random((5,7,3),dtype=np.float32)*.4
    name=next(iter(engine.LOOKS))
    before,full=engine.render_edit(source,name,.5,20,1)
    _,none=engine.render_edit(source,name,.5,20,0)
    _,half=engine.render_edit(source,name,.5,20,.5)
    np.testing.assert_allclose(none,before)
    np.testing.assert_allclose(half,(before+full)/2,atol=1e-7)
    recipe={'version':1,'name':'Roundtrip','base_look':name,'exposure_ev':.5,
            'temperature':20,'strength':.5}
    path=tmp_path/'recipe.json'
    path.write_text(json.dumps(recipe))
    registry=engine.LOOKS.copy()
    key=user_library.import_profile(path,registry)
    engine.LOOKS[key]=registry[key]
    try:
        np.testing.assert_allclose(engine.render_edit(source,key)[1],half,atol=1e-7)
        np.testing.assert_allclose(engine.apply_look(source,key),half,atol=1e-7)
    finally: engine.LOOKS.pop(key)


def test_export_strips_match_preview_pipeline(tmp_path,monkeypatch):
    source=np.random.default_rng(9).random((513,19,3),dtype=np.float32)*.5
    name=next(iter(engine.LOOKS))
    _,preview=engine.render_edit(source,name,.4,-17,.6)
    expected=engine.uint8(apply_grain(preview,'Fuerte'))
    captured=[]
    original=engine.Image.fromarray
    def capture(array):
        captured.append(array.copy())
        return original(array)
    monkeypatch.setattr(engine.Image,'fromarray',capture)
    engine.export_jpeg(source,name,tmp_path/'edited.jpg',grain='Fuerte',
                       exposure_ev=.4,temperature=-17,intensity=.6)
    np.testing.assert_array_equal(captured[0],expected)


def test_raw_archive_preserves_bytes_and_records_edit(tmp_path):
    source=tmp_path/'sample.arw'
    content=b'untouched sensor data'*1000
    source.write_bytes(content)
    output=tmp_path/'edit.zip'
    name=next(iter(engine.LOOKS))
    export_raw_bundle(source,name,output,grain='Suave',exposure_ev=.7,temperature=13,intensity=.4)
    assert source.read_bytes()==content
    with zipfile.ZipFile(output) as archive:
        assert archive.read('original/sample.arw')==content
        info=json.loads(archive.read('export-info.json'))
        assert info['original_sha256']==hashlib.sha256(content).hexdigest()
        assert info['raw_modified'] is False
        recipe=json.loads(archive.read('edit.recipe.json'))
        user_library.validate_recipe(recipe,engine.LOOKS)
        assert recipe['exposure_ev']==.7 and recipe['strength']==.4
        assert str(tmp_path).encode() not in archive.read('export-info.json')
    with pytest.raises(ValueError): export_raw_bundle(source,name,tmp_path/'wrong.arw')


def test_raw_bundle_includes_portable_custom_lut(tmp_path,monkeypatch):
    path=tmp_path/'identity.cube'
    rows=['LUT_3D_SIZE 2']+[f'{r} {g} {b}' for b in (0,1) for g in (0,1) for r in (0,1)]
    path.write_text('\n'.join(rows))
    registry=engine.LOOKS.copy()
    key=user_library.import_profile(path,registry)
    engine.LOOKS[key]=registry[key]
    try:
        source=tmp_path/'source.arw'
        source.write_bytes(b'raw bytes')
        output=tmp_path/'portable.zip'
        export_raw_bundle(source,key,output)
        restored=tmp_path/'restored'
        restored.mkdir()
        with zipfile.ZipFile(output) as archive:
            for name in archive.namelist():
                if name.startswith('library/'):
                    (restored/Path(name).name).write_bytes(archive.read(name))
        monkeypatch.setenv('FILM_POC_USER_DIR',str(restored))
        loaded={}
        assert user_library.load_library(loaded)==[]
        assert key in loaded
        sample=np.array([[[.1,.3,.7]]],dtype=np.float32)
        np.testing.assert_allclose(user_library.apply(sample,loaded[key]),sample,atol=1e-7)
    finally: engine.LOOKS.pop(key)
