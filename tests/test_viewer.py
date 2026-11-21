import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from film_poc.ui import Window
from film_poc.ui.viewer import CompareView


def make_view(width=800, height=600):
    app = QApplication.instance() or QApplication([])
    view = CompareView()
    view.resize(width, height)
    view.show()
    pixmap = QPixmap(1600, 1200)
    pixmap.fill(Qt.GlobalColor.gray)
    view.set_images(pixmap, pixmap)
    app.processEvents()
    return view


def test_fit_then_zoom_and_back():
    view = make_view()
    assert view.fit and view.zoom_percent() == 50  # 800 / 1600
    view.zoom_by(2)
    assert not view.fit and view.zoom_percent() == 100
    view.fit_view()
    assert view.fit and view.zoom_percent() == 50


def test_zoom_keeps_the_point_under_the_cursor_fixed():
    view = make_view()
    anchor = QPointF(600, 150)
    rect = view.image_rect()
    before = ((anchor.x()-rect.x())/rect.width(), (anchor.y()-rect.y())/rect.height())
    view.zoom_by(4, anchor)
    rect = view.image_rect()
    after = ((anchor.x()-rect.x())/rect.width(), (anchor.y()-rect.y())/rect.height())
    assert abs(before[0]-after[0]) < 1e-6 and abs(before[1]-after[1]) < 1e-6


def test_zoom_is_limited():
    view = make_view()
    for _ in range(40):
        view.zoom_by(2)
    assert view.zoom_percent() == 1600
    for _ in range(60):
        view.zoom_by(.5)
    assert view.zoom_percent() == 10


def test_divider_drag_moves_the_split():
    view = make_view()
    assert view.split == .5
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=QPointF(400, 300).toPoint())
    QTest.mouseMove(view, QPointF(200, 300).toPoint())
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=QPointF(200, 300).toPoint())
    assert abs(view.split - .25) < .01


def test_modes_and_keys():
    view = make_view()
    view.set_mode('before')
    assert view.mode == 'before'
    view.set_mode('nonsense')
    assert view.mode == 'before'
    view.set_mode('split')
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert view.split > .5
    QTest.keyClick(view, Qt.Key.Key_1)
    assert view.zoom_percent() == 100
    QTest.keyClick(view, Qt.Key.Key_0)
    assert view.fit


def test_pan_stays_inside_the_photo():
    view = make_view()
    view.zoom_by(4)
    view.centre = QPointF(5, -5)
    view._clamp()
    assert 0 <= view.centre.x() <= 1 and 0 <= view.centre.y() <= 1


class FakeDrop:
    def __init__(self, *paths):
        self.data = QMimeData()
        self.data.setUrls([QUrl.fromLocalFile(p) for p in paths])

    def mimeData(self):
        return self.data


def test_window_accepts_only_raw_drops(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    assert window._dropped_raw(FakeDrop(str(tmp_path/'photo.ARW'))) == tmp_path/'photo.ARW'
    assert window._dropped_raw(FakeDrop(str(tmp_path/'notes.txt'), str(tmp_path/'a.arw'))) \
        == tmp_path/'a.arw'
    assert window._dropped_raw(FakeDrop(str(tmp_path/'notes.txt'))) is None
    window.close()


def test_photo_meta_uses_the_decoder_label(tmp_path, wait_window):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    window.loaded(tmp_path/'a.arw', np.full((40, 60, 3), .2, np.float32))
    assert '60 × 40' in window.photo_meta.text() and '.ARW' in window.photo_meta.text()
    window.loaded(tmp_path/'a.unknown', np.full((40, 60, 3), .2, np.float32))
    assert window.photo_meta.text().endswith('RAW')
    wait_window(window)
    window.close()
