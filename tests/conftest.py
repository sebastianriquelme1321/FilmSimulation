import pytest


@pytest.fixture(autouse=True)
def isolated_user_library(monkeypatch,tmp_path):
    monkeypatch.setenv('FILM_POC_USER_DIR',str(tmp_path/'library'))


@pytest.fixture
def wait_window():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop,QTimer
    def wait(window):
        QApplication.processEvents()
        def pending():
            return (window.gallery_job is not None or window.preview_job is not None
                    or window.preview_pending is not None or window.render_timer.isActive())
        if pending():
            loop=QEventLoop()
            poll=QTimer()
            poll.setInterval(10)
            poll.timeout.connect(lambda: None if pending() else loop.quit())
            timeout=QTimer()
            timeout.setSingleShot(True)
            timeout.timeout.connect(loop.quit)
            poll.start()
            timeout.start(45000)
            loop.exec()
            poll.stop()
            timeout.stop()
        assert not pending(), 'Preview worker did not finish'
        QApplication.processEvents()
    return wait
