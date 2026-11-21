import json
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtWidgets import QApplication, QFileDialog

from film_poc.adapters import storage
from film_poc.services import preferences
from film_poc.ui import Window


def test_export_dir_round_trip_and_missing_folder(tmp_path):
    assert preferences.load_export_dir() is None
    folder = tmp_path/'exports'
    folder.mkdir()
    preferences.save_export_dir(folder)
    assert preferences.load_export_dir() == folder
    folder.rmdir()
    assert preferences.load_export_dir() is None  # no longer available: fall back


def test_export_dir_ignores_bad_values(tmp_path):
    root = storage.library_dir()
    root.mkdir(parents=True)
    for bad in (None, 5, '', ['x'], {'a': 1}):
        (root/'appearance.json').write_text(json.dumps({'export_dir': bad}))
        assert preferences.load_export_dir() is None
    (root/'appearance.json').write_text('not json')
    assert preferences.load_export_dir() is None


def test_export_dir_keeps_the_other_preferences(tmp_path):
    root = storage.library_dir()
    root.mkdir(parents=True)
    (root/'appearance.json').write_text(json.dumps({'theme': 'glass', 'surround': 'Negro'}))
    preferences.save_export_dir(tmp_path)
    data = json.loads((root/'appearance.json').read_text())
    assert data == {'theme': 'glass', 'surround': 'Negro', 'export_dir': str(tmp_path)}
    storage.save_theme_name('darkroom')  # saving another key keeps the folder
    assert preferences.load_export_dir() == tmp_path


def test_window_defaults_to_the_last_export_folder(tmp_path, monkeypatch, wait_window):
    QApplication.instance() or QApplication([])
    window = Window()
    window.gallery.look.setCurrentIndex(0)
    source = tmp_path/'photos'/'input.arw'
    source.parent.mkdir()
    source.write_bytes(b'raw')
    window.loaded(source, np.full((30, 40, 3), .1, dtype=np.float32))
    wait_window(window)
    seen = []
    target = tmp_path/'elsewhere'
    target.mkdir()
    chosen = [target]  # where the (simulated) user saves each time

    def dialog(parent, title, default, formats):
        seen.append(default)
        return str(chosen[0]/'out.jpg'), ''
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', dialog)
    monkeypatch.setattr(window, 'run_job',
                        lambda operation, callback, message: callback(operation()))
    window.save()
    assert os.path.dirname(seen[0]) == str(source.parent)       # first time: next to the photo
    assert preferences.load_export_dir() == target               # remembered after exporting
    window.save()
    assert os.path.dirname(seen[1]) == str(target)               # next time: last folder
    target_files = sorted(p.name for p in target.iterdir())
    assert 'out.jpg' in target_files
    for entry in target.iterdir():
        entry.unlink()
    target.rmdir()
    chosen[0] = source.parent
    window.save()
    assert os.path.dirname(seen[2]) == str(source.parent)        # folder gone: back to the photo's
    wait_window(window)
    window.close()
