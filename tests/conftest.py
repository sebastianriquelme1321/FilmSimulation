import time

import pytest

WAIT_SECONDS = 60


@pytest.fixture(scope='session',autouse=True)
def installed_adapters():
    from film_poc.services.library import install
    install()


@pytest.fixture(autouse=True)
def isolated_user_library(monkeypatch,tmp_path):
    monkeypatch.setenv('FILM_POC_USER_DIR',str(tmp_path/'library'))


def join_workers(window):
    """Block until every background QThread owned by the window has really exited."""
    from PySide6.QtCore import QThread
    for thread in window.findChildren(QThread):
        thread.wait(int(WAIT_SECONDS*1000))
        assert not thread.isRunning(), 'Background worker did not exit'


@pytest.fixture
def wait_window():
    """Pump the event loop until the window has no pending render or worker, with a deadline."""
    from PySide6.QtWidgets import QApplication
    def wait(window):
        def pending():
            return (window.gallery_job is not None or window.preview_job is not None
                    or window.preview_pending is not None or window.render_timer.isActive())
        deadline=time.monotonic()+WAIT_SECONDS
        QApplication.processEvents()
        while pending() and time.monotonic()<deadline:
            QApplication.processEvents()
            time.sleep(.005)
        assert not pending(), 'Preview worker did not finish'
        join_workers(window)
        QApplication.processEvents()
    return wait


@pytest.fixture(autouse=True)
def release_windows(qt_application):
    """After each test, finish deferred closes, join worker threads and destroy windows."""
    yield
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication
    from film_poc.ui import Window
    deadline=time.monotonic()+WAIT_SECONDS
    for window in [w for w in QApplication.topLevelWidgets() if isinstance(w,Window)]:
        window.render_timer.stop()
        window.preview_pending=None
        while ((window.gallery_job is not None or window.preview_job is not None)
               and time.monotonic()<deadline):
            QApplication.processEvents()
            time.sleep(.005)
        for thread in window.findChildren(QThread):
            thread.wait(int(WAIT_SECONDS*1000))
        QApplication.processEvents()
        window.close()
        window.deleteLater()
    QApplication.sendPostedEvents(None,0)
    QApplication.processEvents()


@pytest.fixture(scope='session',autouse=True)
def qt_application():
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
