"""Cached photo-derived ambient backdrop. Image viewers remain neutral gray."""
import numpy as np
from PIL import Image,ImageFilter
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter,QColor,QRadialGradient,QImage,QPixmap
from PySide6.QtCore import Qt


class StudioBackdrop(QWidget):
    def __init__(self,theme):
        super().__init__()
        self.theme=theme
        self.reference_source=None
        self.ambient=None

    def set_reference(self,rgb):
        if rgb is self.reference_source: return
        self.reference_source=rgb
        image=Image.fromarray(rgb).resize((120,80)).filter(ImageFilter.GaussianBlur(13))
        pixels=np.asarray(image).copy()
        qimage=QImage(pixels.data,120,80,pixels.strides[0],QImage.Format.Format_RGB888).copy()
        self.ambient=QPixmap.fromImage(qimage)
        if self.theme=='glass': self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor('#141210' if self.theme=='darkroom' else '#0D0E11'))
        if self.theme=='glass':
            if self.ambient is not None:
                image=self.ambient.scaled(self.size(),Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
                painter.setOpacity(.42)
                painter.drawPixmap((self.width()-image.width())//2,(self.height()-image.height())//2,image)
                painter.setOpacity(1)
                painter.fillRect(self.rect(),QColor(0,0,0,70))
            else:
                glow=QRadialGradient(self.width()*.85,self.height()*.22,max(self.width(),self.height())*.95)
                glow.setColorAt(0,QColor('#755026'))
                glow.setColorAt(1,QColor('#0D0E11'))
                painter.fillRect(self.rect(),glow)
        painter.end()
