from pathlib import Path
import json
import numpy as np
import pytest
from film_poc import user_library


def identity_cube(path):
    rows=['LUT_3D_SIZE 2']
    rows += [f'{r} {g} {b}' for b in (0,1) for g in (0,1) for r in (0,1)]
    path.write_text('\n'.join(rows))


def test_cube_axis_order_and_library_round_trip(tmp_path):
    path=tmp_path/'identity.cube'
    identity_cube(path)
    registry={}
    name=user_library.import_profile(path,registry)
    sample=np.random.default_rng(6).random((5,7,3),dtype=np.float32)
    np.testing.assert_allclose(user_library.apply(sample,registry[name]),sample,atol=1e-7)
    restored={}
    assert user_library.load_library(restored)==[]
    assert name in restored
    assert Path(restored[name]['path']).parent==user_library.library_dir()


def test_reject_incomplete_nonfinite_and_1d_cube(tmp_path):
    path=tmp_path/'bad.cube'
    for text in ('LUT_3D_SIZE 2\n0 0 0','LUT_1D_SIZE 2','LUT_3D_SIZE 2\n'+'nan 0 0\n'*8):
        path.write_text(text)
        with pytest.raises(ValueError): user_library.import_profile(path,{})


def test_invalid_recipe_and_damaged_entry_do_not_load(tmp_path):
    path=tmp_path/'recipe.json'
    path.write_text(json.dumps({'version':1,'name':'Test','base_look':'missing'}))
    with pytest.raises(ValueError): user_library.import_profile(path,{})
    root=user_library.library_dir()
    root.mkdir(parents=True,exist_ok=True)
    (root/'bad.entry.json').write_text('[]')
    assert user_library.load_library({})==['bad.entry.json']


def test_recipe_rejects_recursive_base_and_invalid_metadata():
    registry={'existing':{'backend':'recipe'}}
    with pytest.raises(ValueError):
        user_library.validate_recipe({'version':1,'name':'Test','base_look':'existing'},registry)
    with pytest.raises(ValueError):
        user_library.validate_recipe({'version':1,'name':'Test','base_look':[]},registry)
