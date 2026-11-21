"""NumPy to Qt image conversion shared by the gallery and the preview panes."""
from PySide6.QtGui import QImage, QPixmap


def pixmap(rgb):
    """Return a detached QPixmap copy of an (h, w, 3) uint8 RGB array."""
    rgb = rgb.copy()
    height, width = rgb.shape[:2]
    image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())
