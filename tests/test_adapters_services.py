import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

import film_poc.adapters as adapters
from film_poc.adapters import film_stock_files, lut_files
from film_poc.adapters.storage import atomic_path, cached_array, library_dir
from film_poc.core import raw
from film_poc.core import render as engine
from film_poc.services import develop, library
from film_poc.services.export_bundle import export_raw_bundle


class FakeDecoder:
    extensions = ('.fakeraw',)
    label = 'Fake .FAKERAW'

    def decode(self, path):
        linear = np.full((8, 8, 3), .25, np.float32)
        return linear, np.full((8, 8, 3), 128, np.uint8)


@pytest.fixture
def fake_decoder():
    raw.register_decoder(FakeDecoder())
    yield
    del raw._decoders['.fakeraw']


def test_load_decoders_is_idempotent_and_finds_arw():
    adapters.load_decoders()
    before = dict(raw._decoders)
    adapters.load_decoders()
    assert raw._decoders == before and '.arw' in before


def test_decoder_for_is_case_insensitive_and_message_uses_labels(fake_decoder):
    adapters.load_decoders()
    assert raw.decoder_for(Path('photo.ARW')).label == 'Sony .ARW'
    assert raw.is_supported(Path('x.Arw'))
    with pytest.raises(ValueError) as error:
        raw.decoder_for(Path('photo.xyz'))
    assert 'Sony .ARW / Fake .FAKERAW' in str(error.value)


def test_fake_decoder_is_routed_through_develop(fake_decoder):
    out = develop.decode(Path('shot.FAKERAW'))
    assert out.shape == (8, 8, 3) and np.isfinite(out).all()
    assert '.fakeraw' in raw._decoders


def test_open_filter_follows_registered_decoders(fake_decoder):
    assert develop.open_filter() == 'Sony .ARW / Fake .FAKERAW (*.arw *.ARW *.fakeraw *.FAKERAW)'
    assert develop.supported_labels() == 'Sony .ARW / Fake .FAKERAW'


def test_open_filter_with_only_arw():
    assert develop.open_filter() == 'Sony .ARW (*.arw *.ARW)'


def test_fake_decoder_is_cleaned_up():
    assert '.fakeraw' not in raw._decoders


def test_save_recipe_round_trip_and_invalid(tmp_path):
    name = next(iter(engine.LOOKS))
    recipe = {'version': 1, 'name': 'Saved', 'base_look': name, 'exposure_ev': .5,
              'temperature': 20, 'strength': .5}
    path = tmp_path/'saved.json'
    library.save_recipe(recipe, path)
    assert json.loads(path.read_text(encoding='utf-8')) == recipe
    assert list(tmp_path.glob('*.tmp')) == []
    key = library.import_profile(path)
    try:
        assert engine.edit_settings(key) == (name, {'exposure_ev': .5, 'temperature': 20,
                                                    'intensity': .5})
    finally:
        engine.LOOKS.pop(key)
    bad = tmp_path/'bad.json'
    with pytest.raises(ValueError):
        library.save_recipe({'version': 1, 'name': 'Bad', 'base_look': 'missing'}, bad)
    assert not bad.exists()


def test_atomic_path_error_leaves_destination_and_no_temp(tmp_path):
    destination = tmp_path/'out.txt'
    destination.write_text('old')
    with pytest.raises(RuntimeError):
        with atomic_path(destination) as temporary:
            temporary.write_text('partial')
            raise RuntimeError('boom')
    assert destination.read_text() == 'old'
    assert list(tmp_path.iterdir()) == [destination]


def test_atomic_path_success_replaces(tmp_path):
    destination = tmp_path/'out.txt'
    with atomic_path(destination) as temporary:
        temporary.write_text('new')
    assert destination.read_text() == 'new' and list(tmp_path.iterdir()) == [destination]


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX permission bits')
def test_atomic_path_uses_umask_mode_not_mkstemp_0600(tmp_path):
    mask = os.umask(0)
    os.umask(mask)
    destination = tmp_path/'recipe.json'
    with atomic_path(destination) as temporary:
        temporary.write_text('{}')
    assert destination.stat().st_mode & 0o777 == 0o666 & ~mask


def test_truncated_hald_png_is_a_value_error(tmp_path):
    stock = next(film_stock_files.ASSETS.glob('*.png')).read_bytes()
    broken = tmp_path/'broken.png'
    broken.write_bytes(stock[:len(stock)//2])
    with pytest.raises(ValueError):
        lut_files.read_table(broken)


def test_missing_film_stock_manifest_fails_loudly_and_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(film_stock_files, 'ASSETS', tmp_path)
    film_stock_files.manifest.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            film_stock_files.manifest()
        (tmp_path/'manifest.json').write_text('{}')
        assert film_stock_files.manifest() == {}  # the failure was not cached
    finally:
        film_stock_files.manifest.cache_clear()


def test_cached_array_corrupt_and_shape_mismatch():
    token = 'tok'
    path = library_dir()/'cache'/'ns'/(hashlib.sha256(token.encode()).hexdigest()+'.npy')
    path.parent.mkdir(parents=True)
    path.write_bytes(b'not a numpy file')
    first = cached_array('ns', token, lambda: np.ones((2, 2), np.float32), (2, 2))
    np.testing.assert_array_equal(first, np.ones((2, 2)))
    cached = cached_array('ns', token, lambda: np.zeros((2, 2), np.float32), (2, 2))
    np.testing.assert_array_equal(cached, np.ones((2, 2)))  # served from the rewritten cache
    rebuilt = cached_array('ns', token, lambda: np.zeros((3, 3), np.float32), (3, 3))
    np.testing.assert_array_equal(rebuilt, np.zeros((3, 3)))


def test_install_is_idempotent():
    library.install()
    names = list(engine.LOOKS)
    library.install()
    assert list(engine.LOOKS) == names


def test_use_case_works_in_fresh_interpreter_without_install(tmp_path):
    code = (
        'import sys, numpy as np\n'
        'from film_poc.core.render import LOOKS\n'
        'from film_poc.services.export_jpeg import export_jpeg\n'
        'src = np.full((4, 4, 3), .2, np.float32)\n'
        'for name in [n for n in ("Kodak Portra 400 (película aproximada)",\n'
        '                         "Provia · darktable (experimental)")]:\n'
        '    export_jpeg(src, name, sys.argv[1] + "/" + str(abs(hash(name))) + ".jpg")\n'
        'print("ok")\n')
    result = subprocess.run([sys.executable, '-I', '-c', code, str(tmp_path)], capture_output=True,
                            text=True, env={'FILM_POC_USER_DIR': str(tmp_path/'lib')}, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ok' and len(list(tmp_path.glob('*.jpg'))) == 2


def test_bundle_zip_members_exact(tmp_path):
    source = tmp_path/'sample.arw'
    source.write_bytes(b'raw')
    output = tmp_path/'plain.zip'
    export_raw_bundle(source, next(iter(engine.LOOKS)), output)
    with zipfile.ZipFile(output) as archive:
        assert sorted(archive.namelist()) == sorted(
            ['original/sample.arw', 'edit.recipe.json', 'export-info.json', 'LEEME.txt'])


def test_bundle_zip_members_with_custom_lut(tmp_path):
    cube = tmp_path/'identity.cube'
    rows = ['LUT_3D_SIZE 2']+[f'{r} {g} {b}' for b in (0, 1) for g in (0, 1) for r in (0, 1)]
    cube.write_text('\n'.join(rows))
    key = library.import_profile(cube)
    try:
        source = tmp_path/'sample.arw'
        source.write_bytes(b'raw')
        output = tmp_path/'lut.zip'
        export_raw_bundle(source, key, output)
        digest = hashlib.sha256(cube.read_bytes()).hexdigest()
        with zipfile.ZipFile(output) as archive:
            assert sorted(archive.namelist()) == sorted(
                ['original/sample.arw', 'edit.recipe.json', 'export-info.json', 'LEEME.txt',
                 f'library/{digest}.cube', f'library/{digest}.entry.json'])
    finally:
        engine.LOOKS.pop(key)


def test_decoder_scan_runs_once(monkeypatch):
    monkeypatch.setattr(adapters, '_loaded', False)
    calls = []
    real = adapters.pkgutil.iter_modules

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(adapters.pkgutil, 'iter_modules', counting)
    for _ in range(3):
        adapters.load_decoders()
    assert len(calls) == 1 and '.arw' in raw._decoders
