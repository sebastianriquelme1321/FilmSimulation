import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rawpy
from PIL import Image

from film_poc import adapters
from film_poc.core import raw
from film_poc.core.tone import match_camera_tone
from film_poc.services import develop

EXTENSIONS = ('.arw', '.srf', '.sr2', '.cr2', '.cr3', '.crw', '.nef', '.nrw', '.raf', '.rw2',
              '.orf', '.pef', '.dng', '.srw', '.3fr', '.iiq', '.erf', '.mrw', '.kdc', '.dcr',
              '.raw')


class FakeRaw:
    def __init__(self, thumb=None, thumb_error=None):
        self.thumb, self.thumb_error = thumb, thumb_error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def postprocess(self, **kwargs):
        return np.full((16, 24, 3), 20000, np.uint16)

    def extract_thumb(self):
        if self.thumb_error:
            raise self.thumb_error
        return self.thumb


def jpeg_thumb(size=(200, 120), color=(90, 120, 150)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, 'JPEG')
    return SimpleNamespace(format='JPEG', data=buf.getvalue())


def patch_imread(monkeypatch, fake=None, error=None):
    def imread(path):
        if error:
            raise error
        return fake
    monkeypatch.setattr(rawpy, 'imread', imread)


@pytest.fixture(autouse=True)
def decoders():
    adapters.load_decoders()


@pytest.mark.parametrize('ext', EXTENSIONS)
def test_every_extension_resolves(ext):
    for name in (f'foto{ext}', f'FOTO{ext.upper()}'):
        assert raw.decoder_for(Path(name)).label == 'RAW'
        assert raw.is_supported(Path(name))


def test_filter_and_labels_list_new_extensions():
    flt = develop.open_filter()
    for ext in EXTENSIONS:
        assert f'*{ext}' in flt and f'*{ext.upper()}' in flt
    assert 'RAW' in develop.supported_labels()


def test_jpeg_thumbnail_gives_reference(monkeypatch):
    patch_imread(monkeypatch, FakeRaw(jpeg_thumb()))
    linear, reference = raw.decoder_for(Path('a.NEF')).decode(Path('a.NEF'))
    assert linear.dtype == np.float32 and linear.shape == (16, 24, 3)
    assert reference.dtype == np.uint8 and reference.shape == (120, 200, 3)


def test_bitmap_thumbnail_gives_reference(monkeypatch):
    bitmap = np.full((100, 150, 3), 77, np.uint8)
    patch_imread(monkeypatch, FakeRaw(SimpleNamespace(format='BITMAP', data=bitmap)))
    _, reference = raw.decoder_for(Path('a.cr2')).decode(Path('a.cr2'))
    assert reference.shape == (100, 150, 3)


@pytest.mark.parametrize('error', [rawpy.LibRawNoThumbnailError('x'),
                                   rawpy.LibRawUnsupportedThumbnailError('x')])
def test_missing_thumbnail_gives_none_and_develop_does_not_raise(monkeypatch, error):
    patch_imread(monkeypatch, FakeRaw(thumb_error=error))
    path = Path('a.raf')
    assert raw.decoder_for(path).decode(path)[1] is None
    out = develop.decode(path)
    assert out.dtype == np.float32 and out.shape == (16, 24, 3)
    np.testing.assert_allclose(out, 20000 / 65535, rtol=1e-5)


def test_tiny_and_corrupt_thumbnails_give_none(monkeypatch):
    for thumb in (jpeg_thumb((32, 20)), SimpleNamespace(format='JPEG', data=b'not a jpeg')):
        patch_imread(monkeypatch, FakeRaw(thumb))
        assert raw.decoder_for(Path('a.dng')).decode(Path('a.dng'))[1] is None


def test_none_reference_skips_tone_match_and_clips(monkeypatch):
    class Dec:
        extensions = ('.noref',)
        label = 'x'

        def decode(self, path):
            return np.full((4, 4, 3), 1.5, np.float32), None

    monkeypatch.setattr(raw, '_decoders', dict(raw._decoders))
    raw.register_decoder(Dec())
    out = develop.decode(Path('a.noref'))
    assert out.max() == 1.0 and out.dtype == np.float32


def test_preview_behaviour_unchanged(monkeypatch):
    patch_imread(monkeypatch, FakeRaw(jpeg_thumb()))
    path = Path('a.arw')
    linear, reference = raw.decoder_for(path).decode(path)
    np.testing.assert_array_equal(develop.decode(path), match_camera_tone(linear, reference))


@pytest.mark.parametrize('error', [rawpy.LibRawFileUnsupportedError('x'),
                                   rawpy.LibRawDataError('x'), rawpy.LibRawIOError('x'),
                                   OSError('x'), MemoryError()])
def test_unsupported_file_gives_friendly_error(monkeypatch, error):
    patch_imread(monkeypatch, error=error)
    with pytest.raises(ValueError, match='foto.CR3') as info:
        develop.decode(Path('/tmp/foto.CR3'))
    assert 'modelo de cámara' in str(info.value)
