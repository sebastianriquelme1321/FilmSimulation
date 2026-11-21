"""Ordinary photos (JPEG/PNG/TIFF): decoder, colour handling, EXIF carry-over, window flow."""
import hashlib
import json
import logging
import os
import struct
import zipfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
import pytest
from PIL import Image, ImageCms
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication, QFileDialog

import film_poc.adapters as adapters
from film_poc.adapters import image_decoder
from film_poc.core import raw
from film_poc.core.render import LOOKS
from film_poc.services import develop
from film_poc.services.export_jpeg import export_jpeg
from film_poc.services.metadata import read_exif
from film_poc.ui import Window


def expected_linear(values):
    x = np.asarray(values, np.float64) / 255
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def decode(path):
    adapters.load_decoders()
    return raw.decoder_for(path).decode(path)


def flat(mode, size, colour, path, **options):
    Image.new(mode, size, colour).save(path, **options)
    return path


def srgb_bytes():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def p3_profile():
    """Minimal ICC v2 matrix/TRC profile with Display P3 primaries (D50 adapted), gamma 2.2."""
    def fixed(value):
        return struct.pack('>i', round(value * 65536))

    def xyz(x, y, z):
        return b'XYZ \0\0\0\0' + fixed(x) + fixed(y) + fixed(z)
    text = b'Display P3 test'
    desc = (b'desc\0\0\0\0' + struct.pack('>I', len(text) + 1) + text + b'\0'
            + b'\0' * 8 + b'\0\0' + b'\0' + b'\0' * 67)
    curve = b'curv\0\0\0\0' + struct.pack('>I', 1) + struct.pack('>H', round(2.2 * 256)) + b'\0\0'
    tags = [(b'desc', desc), (b'cprt', b'text\0\0\0\0test\0'),
            (b'wtpt', xyz(.9642, 1.0, .8249)),
            (b'rXYZ', xyz(.5151, .2412, -.0011)), (b'gXYZ', xyz(.2920, .6922, .0419)),
            (b'bXYZ', xyz(.1571, .0666, .7841)),
            (b'rTRC', curve), (b'gTRC', curve), (b'bTRC', curve)]
    table, body = b'', b''
    offset = 128 + 4 + 12 * len(tags)
    for signature, data in tags:
        data += b'\0' * (-len(data) % 4)
        table += signature + struct.pack('>II', offset + len(body), len(data))
        body += data
    size = offset + len(body)
    header = (struct.pack('>I', size) + b'lcms' + struct.pack('>I', 0x02400000) + b'mntrRGB XYZ '
              + b'\0' * 12 + b'acsp' + b'APPL' + b'\0' * 12 + b'\0' * 8 + b'\0\0\0\0'
              + fixed(.9642) + fixed(1.0) + fixed(.8249) + b'\0' * 4 + b'\0' * 44)
    return header + struct.pack('>I', len(tags)) + table + body


def test_srgb_jpeg_round_trip_is_exact_within_8_bit(tmp_path):
    colours = [(0, 0, 0), (255, 255, 255), (10, 20, 30), (128, 64, 200), (255, 0, 0)]
    for colour in colours:
        path = flat('RGB', (16, 16), colour, tmp_path/'a.jpg', quality=100, subsampling=0)
        linear, reference = decode(path)
        assert reference is None and linear.dtype == np.float32 and linear.shape == (16, 16, 3)
        assert np.allclose(linear[8, 8], expected_linear(colour), atol=.012)
        assert 0 <= linear.min() and linear.max() <= 1


def test_transfer_function_matches_the_tone_reference_constants():
    values = np.arange(256)
    table = image_decoder.srgb_to_linear(values / 255)
    assert np.allclose(table, expected_linear(values), atol=1e-6)
    assert table[0] == 0 and table[255] == pytest.approx(1.0, abs=1e-6)


def test_exif_orientation_is_applied(tmp_path):
    image = Image.new('RGB', (32, 16), (0, 0, 255))
    image.paste((255, 0, 0), (0, 0, 16, 8))  # red block, top-left
    exif = Image.Exif()
    exif[0x0112] = 6  # display rotated 90 degrees clockwise
    path = tmp_path/'rot.jpg'
    image.save(path, quality=100, subsampling=0, exif=exif)
    linear, _ = decode(path)
    assert linear.shape == (32, 16, 3)
    assert linear[2, -3, 0] > .9 and linear[2, -3, 2] < .1   # red now top-right
    assert linear[-3, 2, 2] > .9 and linear[-3, 2, 0] < .1


def test_display_p3_is_converted_to_srgb(tmp_path):
    profile = p3_profile()
    path = tmp_path/'p3.jpg'
    Image.new('RGB', (16, 16), (200, 80, 80)).save(path, quality=100, subsampling=0,
                                                    icc_profile=profile)
    linear, _ = decode(path)
    untagged = expected_linear((200, 80, 80))
    assert not np.allclose(linear[8, 8], untagged, atol=.01)          # colours moved
    assert linear[8, 8, 0] - linear[8, 8, 1] > untagged[0] - untagged[1]  # wider gamut
    grey = tmp_path/'p3grey.jpg'
    Image.new('RGB', (16, 16), (120, 120, 120)).save(grey, quality=100, icc_profile=profile)
    neutral, _ = decode(grey)
    assert np.ptp(neutral[8, 8]) < .01                               # neutrals stay neutral


def test_srgb_or_missing_profile_is_left_alone(tmp_path, monkeypatch):
    def forbidden(*_, **__):
        raise AssertionError('should not convert')
    monkeypatch.setattr(ImageCms, 'profileToProfile', forbidden)
    path = flat('RGB', (8, 8), (90, 120, 30), tmp_path/'s.jpg', quality=100, subsampling=0,
                icc_profile=srgb_bytes())
    assert np.allclose(decode(path)[0][4, 4], expected_linear((90, 120, 30)), atol=.006)
    plain = flat('RGB', (8, 8), (90, 120, 30), tmp_path/'n.png')
    assert np.allclose(decode(plain)[0][4, 4], expected_linear((90, 120, 30)), atol=.001)


def test_profile_conversion_path_is_used_for_other_profiles(tmp_path, monkeypatch):
    calls = []
    real = ImageCms.profileToProfile

    def spy(image, source, target, **options):
        calls.append(options)
        return real(image, source, target, **options)
    monkeypatch.setattr(ImageCms, 'profileToProfile', spy)
    path = tmp_path/'p3.png'
    Image.new('RGB', (8, 8), (10, 200, 30)).save(path, icc_profile=p3_profile())
    decode(path)
    assert len(calls) == 1 and calls[0]['outputMode'] == 'RGB'


def test_bad_icc_bytes_warn_and_assume_srgb(tmp_path, caplog):
    path = tmp_path/'bad.jpg'
    Image.new('RGB', (8, 8), (50, 100, 150)).save(path, quality=100, subsampling=0,
                                                   icc_profile=b'this is not an icc profile' * 8)
    with caplog.at_level(logging.WARNING, logger='film_poc.adapters.image_decoder'):
        linear, _ = decode(path)
    assert any(r.name == 'film_poc.adapters.image_decoder' for r in caplog.records)
    assert np.allclose(linear[4, 4], expected_linear((50, 100, 150)), atol=.006)


def test_grayscale_is_replicated_to_rgb(tmp_path):
    linear, _ = decode(flat('L', (8, 8), 100, tmp_path/'g.png'))
    assert linear.shape == (8, 8, 3)
    assert np.allclose(linear[3, 3], expected_linear(100), atol=1e-4)


def test_la_and_rgba_are_composited_over_white(tmp_path):
    transparent = flat('LA', (8, 8), (0, 0), tmp_path/'la.png')
    assert np.allclose(decode(transparent)[0], 1.0, atol=1e-4)
    opaque = flat('RGBA', (8, 8), (255, 0, 0, 255), tmp_path/'rgba.png')
    assert np.allclose(decode(opaque)[0][0, 0], [1, 0, 0], atol=1e-4)
    half = flat('RGBA', (8, 8), (0, 0, 0, 128), tmp_path/'half.png')
    value = decode(half)[0][0, 0]
    assert np.allclose(value, expected_linear(127), atol=.01) and np.ptp(value) < 1e-6


def test_palette_images(tmp_path):
    image = Image.new('P', (8, 8), 0)
    image.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
    image.save(tmp_path/'p.png')
    assert np.allclose(decode(tmp_path/'p.png')[0][0, 0], [1, 0, 0], atol=1e-4)
    image.save(tmp_path/'pt.png', transparency=0)
    assert np.allclose(decode(tmp_path/'pt.png')[0][0, 0], 1.0, atol=1e-4)  # transparent -> white


def test_cmyk_jpeg_becomes_rgb(tmp_path):
    path = flat('CMYK', (16, 16), (0, 0, 0, 0), tmp_path/'c.jpg', quality=100)
    linear, _ = decode(path)
    assert linear.shape == (16, 16, 3) and linear.mean() > .95   # no ink -> white
    black = flat('CMYK', (16, 16), (0, 0, 0, 255), tmp_path/'k.jpg', quality=100)
    assert decode(black)[0].mean() < .05


@pytest.mark.parametrize('suffix', ['.png', '.tif'])
def test_sixteen_bit_grayscale_is_scaled_not_overflowed(tmp_path, suffix):
    data = np.array([[0, 1000, 32768, 65535]] * 2, dtype=np.uint16)
    path = tmp_path/f'deep{suffix}'
    Image.fromarray(data).save(path)
    with Image.open(path) as check:
        assert check.mode.startswith('I')
    linear, _ = decode(path)
    assert linear.shape == (2, 4, 3) and 0 <= linear.min() and linear.max() <= 1
    assert np.allclose(linear[0, :, 0], expected_linear(data[0] / 65535 * 255), atol=1e-4)


def test_tiny_images(tmp_path):
    one, _ = decode(flat('RGB', (1, 1), (255, 128, 0), tmp_path/'one.png'))
    assert one.shape == (1, 1, 3) and one[0, 0, 0] == pytest.approx(1.0)
    thin, _ = decode(flat('RGB', (3, 1), (9, 9, 9), tmp_path/'thin.tif'))
    assert thin.shape == (1, 3, 3)


def test_corrupt_and_truncated_files_name_the_file(tmp_path):
    bad = tmp_path/'broken.jpg'
    bad.write_bytes(b'definitely not a jpeg')
    with pytest.raises(ValueError, match='broken.jpg'):
        decode(bad)
    good = tmp_path/'cut.jpg'
    Image.effect_noise((256, 256), 80).convert('RGB').save(good, quality=95)
    good.write_bytes(good.read_bytes()[:700])
    with pytest.raises(ValueError, match='cut.jpg'):
        decode(good)
    with pytest.raises(ValueError, match='missing.png'):
        decode(tmp_path/'missing.png')


def test_decompression_bomb_policy(tmp_path, monkeypatch):
    assert Image.MAX_IMAGE_PIXELS is not None                    # the check stays enabled
    assert 100_000_000 <= image_decoder.MAX_PIXELS <= 250_000_000
    path = flat('RGB', (40, 40), (1, 2, 3), tmp_path/'big.png')
    monkeypatch.setattr(image_decoder, 'MAX_PIXELS', 1000)
    with pytest.raises(ValueError, match='big.png'):
        decode(path)


def test_unsupported_extension_keeps_the_registry_error(tmp_path):
    adapters.load_decoders()
    with pytest.raises(ValueError, match='Este POC acepta archivos'):
        raw.decoder_for(tmp_path/'photo.bmp')


@pytest.mark.parametrize('name', ['a.jpg', 'a.JPG', 'a.Jpeg', 'a.PNG', 'a.tif', 'a.TIFF'])
def test_extensions_resolve_case_insensitively(name):
    adapters.load_decoders()
    assert raw.is_supported(Path(name)) and raw.decoder_for(Path(name)).label == 'Imagen'
    assert raw.format_label(Path(name)) in ('JPEG', 'PNG', 'TIFF')
    assert raw.format_label(Path('x.ARW')) == 'RAW'


def test_filter_and_labels_cover_raw_and_images():
    flt = develop.open_filter()
    assert develop.supported_labels() == 'RAW / Imagen'
    for extension in ('.arw', '.jpg', '.jpeg', '.png', '.tif', '.tiff'):
        assert f'*{extension} *{extension.upper()}' in flt
    for group in flt.split(';;'):
        assert group.count('(') == 1 and group.endswith(')') and ' (*.' in group


def test_develop_decode_skips_tone_matching_for_photos(tmp_path, monkeypatch):
    def forbidden(*_):
        raise AssertionError('tone match called')
    monkeypatch.setattr(develop, 'match_camera_tone', forbidden)
    out = develop.decode(flat('RGB', (8, 8), (255, 255, 255), tmp_path/'w.jpg', quality=100))
    assert out.dtype == np.float32 and out.max() <= 1 and out.min() >= 0
    assert np.allclose(out, 1.0, atol=.004)


# ---- EXIF ------------------------------------------------------------------------------------

def jpeg_with_exif(path, orientation=6):
    exif = Image.Exif()
    exif[0x010F], exif[0x0110], exif[0x0132] = 'ACME', 'Cam 1', '2024:05:06 07:08:09'
    exif[0x0112] = orientation
    details = exif.get_ifd(0x8769)
    details[0x829A], details[0x829D], details[0xA434] = (1 / 250), 2.8, 'Lens 35mm'
    details[0x927C] = b'maker note bytes'
    Image.new('RGB', (48, 32), (120, 90, 60)).save(path, quality=92, exif=exif)
    return path


def test_read_exif_keeps_camera_fields_and_resets_orientation(tmp_path):
    block = read_exif(jpeg_with_exif(tmp_path/'e.jpg'))
    out = tmp_path/'copy.jpg'
    Image.new('RGB', (8, 8)).save(out, exif=block)
    exif = Image.open(out).getexif()
    assert (exif[0x010F], exif[0x0110], exif[0x0132]) == ('ACME', 'Cam 1', '2024:05:06 07:08:09')
    assert exif[0x0112] == 1
    details = exif.get_ifd(0x8769)
    assert details[0xA434] == 'Lens 35mm' and float(details[0x829D]) == pytest.approx(2.8)
    assert 0x927C not in details


def test_read_exif_is_none_without_exif_for_raw_and_on_errors(tmp_path, monkeypatch, caplog):
    assert read_exif(flat('RGB', (8, 8), (1, 2, 3), tmp_path/'n.jpg')) is None
    assert read_exif(tmp_path/'shot.ARW') is None
    assert read_exif(tmp_path/'missing.jpg') is None
    path = jpeg_with_exif(tmp_path/'w.jpg')

    def boom(self):
        raise ValueError('weird exif')
    monkeypatch.setattr(Image.Exif, 'tobytes', boom)
    with caplog.at_level(logging.WARNING, logger='film_poc.services.metadata'):
        assert read_exif(path) is None
    assert any('w.jpg' in r.getMessage() for r in caplog.records)


def test_export_jpeg_embeds_exif_and_stays_compatible(tmp_path):
    linear = np.full((20, 30, 3), .2, np.float32)
    name = next(iter(LOOKS))
    plain = tmp_path/'plain.jpg'
    export_jpeg(linear, name, plain)
    assert not Image.open(plain).getexif().get(0x010F)
    block = read_exif(jpeg_with_exif(tmp_path/'src.jpg'))
    tagged = tmp_path/'tagged.jpg'
    export_jpeg(linear, name, tagged, exif=block)
    with Image.open(tagged) as image:
        assert image.getexif()[0x010F] == 'ACME' and image.info.get('icc_profile')


# ---- window ----------------------------------------------------------------------------------

class FakeDrop:
    def __init__(self, *paths):
        self.data = QMimeData()
        self.data.setUrls([QUrl.fromLocalFile(p) for p in paths])

    def mimeData(self):
        return self.data


def test_window_accepts_image_drops(tmp_path):
    QApplication.instance() or QApplication([])
    window = Window()
    for name in ('a.jpg', 'b.JPEG', 'c.png', 'd.TIF'):
        assert window._dropped_raw(FakeDrop(str(tmp_path/name))) == tmp_path/name
    assert window._dropped_raw(FakeDrop(str(tmp_path/'e.gif'))) is None
    window.close()


def test_window_wording_and_job_messages(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    window = Window()
    assert window.open_button.text() == 'Importar foto'
    assert 'foto' in window.photo_meta.text() and 'foto' in window.viewer.placeholder
    messages = []
    monkeypatch.setattr(window, 'run_job', lambda op, cb, message: messages.append(message))
    window.open_path(tmp_path/'a.jpg')
    window.open_path(tmp_path/'a.arw')
    assert messages == ['Abriendo foto…', 'Revelando RAW…']
    window.close()


def test_open_jpeg_end_to_end_with_exif_and_bundle(tmp_path, monkeypatch, wait_window):
    QApplication.instance() or QApplication([])
    source = jpeg_with_exif(tmp_path/'IMG_0001.jpg')
    window = Window()
    window.gallery.look.setCurrentIndex(0)
    assert window.export_format.itemText(1) == 'RAW original + ajustes (.zip)'
    monkeypatch.setattr(window, 'run_job',
                        lambda operation, callback, message: callback(operation()))
    window.open_path(source)
    wait_window(window)
    assert window.photo_meta.text() == '32 × 48 · JPEG'          # orientation 6 swapped the sides
    assert window.photo_title.text() == 'IMG_0001.jpg'
    assert len(window.pixmaps) == 2 and all(not p.isNull() for p in window.pixmaps)
    assert window.export_format.itemText(1) == 'Original + ajustes (.zip)'
    assert 'RAW' not in window.export_format.toolTip()
    out = tmp_path/'out.jpg'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(out), ''))
    window.save()
    with Image.open(out) as result:
        assert result.size == (32, 48)
        exif = result.getexif()
        assert exif[0x010F] == 'ACME' and exif[0x0112] == 1
        assert exif.get_ifd(0x8769)[0xA434] == 'Lens 35mm'
    window.export_format.setCurrentIndex(1)
    dialog = []
    zip_out = tmp_path/'bundle.zip'

    def save_dialog(parent, title, default, formats):
        dialog.append((title, default))
        return str(zip_out), ''
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', save_dialog)
    window.save()
    assert dialog[0][0] == 'Original + ajustes (sin look incorporado)'
    assert dialog[0][1].endswith('.zip')
    original = source.read_bytes()
    with zipfile.ZipFile(zip_out) as archive:
        assert archive.read('original/IMG_0001.jpg') == original
        info = json.loads(archive.read('export-info.json'))
        assert info['original_sha256'] == hashlib.sha256(original).hexdigest()
        assert info['original_modified'] is False and 'edit.recipe.json' in archive.namelist()
        assert 'IMG_0001.jpg' in archive.read('LEEME.txt').decode()
    wait_window(window)
    window.close()


def test_raw_source_keeps_the_raw_wording(tmp_path, wait_window):
    QApplication.instance() or QApplication([])
    window = Window()
    window.loaded(tmp_path/'x.arw', np.full((20, 30, 3), .1, np.float32))
    assert window.photo_meta.text().endswith('RAW')
    assert window.export_format.itemText(1) == 'RAW original + ajustes (.zip)'
    window.loaded(tmp_path/'y.png', np.full((20, 30, 3), .1, np.float32))
    assert window.photo_meta.text().endswith('PNG')
    assert window.export_format.itemText(1) == 'Original + ajustes (.zip)'
    window.loaded(tmp_path/'z.ARW', np.full((20, 30, 3), .1, np.float32))
    assert window.export_format.itemText(1) == 'RAW original + ajustes (.zip)'
    wait_window(window)
    window.close()
