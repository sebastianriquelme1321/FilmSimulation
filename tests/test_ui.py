import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtWidgets import QApplication
from film_poc.ui import Window, Job


def test_window_render_and_background_job(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    assert not window.save_button.isEnabled()
    window.loaded((tmp_path / 'synthetic.arw', np.full((100, 160, 3), .18, dtype=np.float32)))
    window.set_busy(False)
    assert window.save_button.isEnabled()
    assert len(window.pixmaps) == 2
    assert all(not pixmap.isNull() for pixmap in window.pixmaps)
    assert window.look.count() == 31
    for index in range(window.look.count()):
        window.look.setCurrentIndex(index)
        assert all(not pixmap.isNull() for pixmap in window.pixmaps)
    received = []
    job = Job(lambda: 42, window)
    job.done.connect(received.append)
    job.start()
    assert job.wait(5000)
    app.processEvents()
    assert received == [42]
    window.close()
