import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtWidgets import QApplication, QFileDialog
from film_poc import ui
from film_poc.ui.jobs import Job
from film_poc.catalog import reference_linear
from film_poc.adapters.storage import library_dir


def test_busy_window_ignores_open_save_import_and_render(tmp_path,monkeypatch,wait_window):
    QApplication.instance() or QApplication([])
    window = ui.Window()
    wait_window(window)
    window.loaded(tmp_path/'x.arw',np.full((100,160,3),.18,dtype=np.float32))
    wait_window(window)
    def forbidden(*_,**__): raise AssertionError('dialog opened while busy')
    monkeypatch.setattr(QFileDialog,'getOpenFileName',forbidden)
    monkeypatch.setattr(QFileDialog,'getSaveFileName',forbidden)
    monkeypatch.setattr(window,'run_job',forbidden)
    window.set_busy(True)
    revision = window.preview_revision
    window.open_raw(); window.save(); window.import_custom(); window.save_recipe(); window.render()
    assert window.preview_revision == revision
    monkeypatch.undo()
    window.set_busy(False)
    assert window.preview_revision == revision + 1
    wait_window(window)
    window.close()


def test_job_failure_emits_failed_and_logs(caplog,wait_window):
    QApplication.instance() or QApplication([])
    errors = []
    def boom(): raise RuntimeError('kaput')
    job = Job(boom,None)
    job.failed.connect(errors.append)
    with caplog.at_level('ERROR'):
        job.run()
    assert errors == ['kaput']
    assert 'kaput' in caplog.text


def test_corrupt_reference_image_falls_back():
    path = library_dir()/'reference.jpg'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'not a jpeg')
    assert reference_linear().shape == (160,240,3)
