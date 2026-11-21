"""Photo viewer: one canvas with zoom, pan and a draggable before/after divider."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

MODES = ('split', 'before', 'after')
SURROUNDS = {'Gris': '#303030', 'Negro': '#0A0A0A', 'Blanco': '#E6E6E6'}  # neutral viewer backdrops
MIN_ZOOM, MAX_ZOOM = .1, 16.
GRAB = 10  # px either side of the divider that still grabs it


class CompareView(QWidget):
    """Shows `before` and `after` pixmaps of the same photo; neutral gray, no theme colours."""

    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('compareView')
        self.setMinimumSize(320, 240)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Visor de la foto: antes y después')
        self.before = None
        self.after = None
        self.placeholder = ''
        self.before_label = 'Antes'
        self.after_label = 'Después'
        self.surround = SURROUNDS['Gris']
        self.mode = 'split'
        self.split = .5          # divider position as a fraction of the widget width
        self.fit = True
        self.zoom = 1.
        self.centre = QPointF(.5, .5)  # image point (0-1 each axis) shown at the view centre
        self._drag = None        # 'divider' | ('pan', last_pos) | None

    # ---- content ------------------------------------------------------------------------

    def set_images(self, before, after):
        """Show new pixmaps (either may be None); keep the current zoom and divider."""
        first = self.before is None and self.after is None
        self.before, self.after = before, after
        if first:
            self.fit_view()
        self.update()

    def set_placeholder(self, text):
        self.placeholder = text
        self.update()

    def set_after_label(self, text):
        self.after_label = text
        self.update()

    def set_surround(self, name):
        """Neutral backdrop behind the photo: 'Gris', 'Negro' or 'Blanco'."""
        if name in SURROUNDS:
            self.surround = SURROUNDS[name]
            self.update()

    def set_mode(self, mode):
        """'split' (divider), 'before' or 'after'."""
        if mode in MODES and mode != self.mode:
            self.mode = mode
            self.update()

    def set_split(self, fraction):
        self.split = min(max(fraction, 0.), 1.)
        self.update()

    # ---- geometry -----------------------------------------------------------------------

    def _size(self):
        image = self.after or self.before
        return (image.width(), image.height()) if image else (0, 0)

    def _fit_zoom(self):
        width, height = self._size()
        if not width or not height:
            return 1.
        return min(self.width()/width, self.height()/height)

    def _scale(self):
        return self._fit_zoom() if self.fit else self.zoom

    def image_rect(self):
        """Where the photo is painted, in widget coordinates."""
        width, height = self._size()
        scale = self._scale()
        w, h = width*scale, height*scale
        if self.fit:
            return QRectF((self.width()-w)/2, (self.height()-h)/2, w, h)
        x = self.width()/2 - self.centre.x()*w
        y = self.height()/2 - self.centre.y()*h
        return QRectF(x, y, w, h)

    def zoom_percent(self):
        return round(self._scale()*100)

    # ---- zoom / pan ---------------------------------------------------------------------

    def _set_zoom(self, zoom, anchor=None):
        """Zoom to `zoom`, keeping the image point under `anchor` (widget px) fixed."""
        width, height = self._size()
        if not width:
            return
        rect = self.image_rect()
        anchor = anchor or QPointF(self.width()/2, self.height()/2)
        point = QPointF((anchor.x()-rect.x())/rect.width(), (anchor.y()-rect.y())/rect.height())
        self.fit = False
        self.zoom = min(max(zoom, MIN_ZOOM), MAX_ZOOM)
        w, h = width*self.zoom, height*self.zoom
        self.centre = QPointF(point.x() + (self.width()/2-anchor.x())/w,
                              point.y() + (self.height()/2-anchor.y())/h)
        self._clamp()
        self.update()
        self.zoom_changed.emit(self.zoom)

    def _clamp(self):
        self.centre = QPointF(min(max(self.centre.x(), 0.), 1.), min(max(self.centre.y(), 0.), 1.))

    def zoom_by(self, factor, anchor=None):
        self._set_zoom(self._scale()*factor, anchor)

    def fit_view(self):
        self.fit = True
        self.centre = QPointF(.5, .5)
        self.update()
        self.zoom_changed.emit(self._fit_zoom())

    def actual_size(self):
        """One image pixel per device-independent pixel, centred."""
        self.centre = QPointF(.5, .5)
        self._set_zoom(1.)

    def toggle_zoom(self, anchor=None):
        if self.fit and self._fit_zoom() < 1.:
            self._set_zoom(1., anchor)
        else:
            self.fit_view()

    # ---- painting -----------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = QPainterPath()
        outline.addRoundedRect(QRectF(self.rect()).adjusted(.5, .5, -.5, -.5), 12, 12)
        painter.fillPath(outline, QColor(self.surround))
        painter.setClipPath(outline)
        if self.after is None and self.before is None:
            self._paint_placeholder(painter)
        else:
            self._paint_photo(painter)
        painter.setClipping(False)
        painter.setBrush(Qt.BrushStyle.NoBrush)  # the last pill left a translucent brush
        painter.setPen(QPen(QColor(self.surround).lighter(115), 1))
        painter.drawPath(outline)
        painter.end()

    def _paint_placeholder(self, painter):
        painter.setPen(QColor('#444444' if QColor(self.surround).lightness() > 128 else '#C0C0C0'))
        painter.drawText(self.rect().adjusted(24, 24, -24, -24),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         self.placeholder)

    def _paint_photo(self, painter):
        rect = self.image_rect()
        after = self.after
        before = self.before
        divider = self.width()*self.split
        if self.mode == 'before' or after is None:
            painter.drawPixmap(rect, before or after, QRectF((before or after).rect()))
            self._pill(painter, self.before_label, 14, 14, left=True)
            return
        if self.mode == 'after' or before is None:
            painter.drawPixmap(rect, after, QRectF(after.rect()))
            self._pill(painter, self.after_label, self.width()-14, 14, left=False)
            return
        painter.drawPixmap(rect, after, QRectF(after.rect()))
        painter.save()
        painter.setClipRect(QRectF(0, 0, divider, self.height()))
        painter.drawPixmap(rect, before, QRectF(before.rect()))
        painter.restore()
        painter.setPen(QPen(QColor(255, 255, 255, 230), 2))
        painter.drawLine(QPointF(divider, 0), QPointF(divider, self.height()))
        centre = QPointF(divider, self.height()/2)
        painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(centre, 15, 15)
        painter.setPen(QPen(QColor('#303030'), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for side in (-1, 1):
            tip = QPointF(centre.x()+side*6, centre.y())
            painter.drawLine(tip, QPointF(tip.x()-side*4, tip.y()-4))
            painter.drawLine(tip, QPointF(tip.x()-side*4, tip.y()+4))
        self._pill(painter, self.before_label, 14, 14, left=True)
        self._pill(painter, self.after_label, self.width()-14, 14, left=False)

    def _pill(self, painter, text, x, y, left):
        font = QFont(painter.font())
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        width = min(painter.fontMetrics().horizontalAdvance(text) + 20, self.width()//2 - 24)
        box = QRectF(x if left else x-width, y, width, 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 18, 16, 190))
        painter.drawRoundedRect(box, 12, 12)
        painter.setPen(QColor('#F2EDE4'))
        elided = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, int(width-16))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, elided)

    # ---- input --------------------------------------------------------------------------

    def _on_divider(self, x):
        return (self.mode == 'split' and self.before is not None and self.after is not None
                and abs(x - self.width()*self.split) <= GRAB)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setFocus()
        if self._on_divider(event.position().x()):
            self._drag = 'divider'
        elif not self.fit or self._fit_zoom() < 1.:
            self._drag = ('pan', event.position())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        position = event.position()
        if self._drag == 'divider':
            self.set_split(position.x()/self.width())
        elif isinstance(self._drag, tuple):
            last = self._drag[1]
            rect = self.image_rect()
            if not self.fit and rect.width() and rect.height():
                self.centre = QPointF(self.centre.x() - (position.x()-last.x())/rect.width(),
                                      self.centre.y() - (position.y()-last.y())/rect.height())
                self._clamp()
                self.update()
            self._drag = ('pan', position)
        elif self._on_divider(position.x()):
            self.setCursor(Qt.CursorShape.SplitHCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor if not self.fit
                           else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._drag = None
        self.unsetCursor()

    def mouseDoubleClickEvent(self, event):
        if not self._on_divider(event.position().x()):
            self.toggle_zoom(event.position())

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta:
            self.zoom_by(1.0015**delta, event.position())
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(1.25)
        elif key == Qt.Key.Key_Minus:
            self.zoom_by(.8)
        elif key == Qt.Key.Key_0:
            self.fit_view()
        elif key == Qt.Key.Key_1:
            self.actual_size()
        elif key == Qt.Key.Key_Left and self.mode == 'split':
            self.set_split(self.split - .02)
        elif key == Qt.Key.Key_Right and self.mode == 'split':
            self.set_split(self.split + .02)
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit:
            self.zoom_changed.emit(self._fit_zoom())
        self.update()
