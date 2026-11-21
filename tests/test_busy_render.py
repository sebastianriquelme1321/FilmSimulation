import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtWidgets import QApplication

from film_poc import ui


def make_window(wait_window):
    QApplication.instance() or QApplication([])
    window = ui.Window()
    wait_window(window)
    return window


def settle(window, wait_window):
    """Pump events until the foreground job has finished and busy is cleared."""
    end = time.monotonic() + 30
    while window.busy and time.monotonic() < end:
        QApplication.processEvents()
        time.sleep(.005)
    assert not window.busy
    wait_window(window)


def test_load_via_job_renders_after_busy_clears(tmp_path, wait_window):
    window = make_window(wait_window)
    linear = np.full((100, 160, 3), .18, dtype=np.float32)
    window.run_job(lambda: linear, lambda image: window.loaded(tmp_path / 'x.arw', image), 'x')
    settle(window, wait_window)
    assert window.pixmaps and window.pixmaps[0] is not None
    window.close()


def test_finished_export_or_failed_job_does_not_render(tmp_path, wait_window, monkeypatch):
    window = make_window(wait_window)
    window.loaded(tmp_path / 'x.arw', np.full((100, 160, 3), .18, dtype=np.float32))
    wait_window(window)
    starts = []
    original = window.start_preview
    monkeypatch.setattr(window, 'start_preview', lambda: (starts.append(1), original())[1])
    monkeypatch.setattr(window, 'error', lambda message: None)
    revision = window.preview_revision
    window.run_job(lambda: None, lambda _: None, 'export')
    settle(window, wait_window)
    window.run_job(lambda: 1 / 0, lambda _: None, 'fails')
    settle(window, wait_window)
    assert not starts
    assert window.preview_revision == revision
    window.close()
