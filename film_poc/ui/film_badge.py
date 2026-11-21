"""Original vector illustration for catalog cards; generic, no product photos/logos/brand marks."""
from zlib import crc32

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

BRANDS = ('kodak', 'ilford', 'fujifilm', 'fuji', 'darktable')   # never drawn on the badge
MONO = ('hp5', 'acros', 'mono', 'b&w', 'neopan', 'tri-x')
PALETTE = (('#c98f5b', '#202124'), ('#6f8fb3', '#ffffff'), ('#8a9a5b', '#202124'),
           ('#b5655c', '#ffffff'), ('#7d6fa8', '#ffffff'), ('#538466', '#ffffff'))


def badge_style(label):
    """(background, ink, name words) for a generic badge: no brand names or brand colours."""
    words = [w for w in label.replace('Kodachrome', 'Koda chrome').split()
             if w.lower() not in BRANDS]
    name = ' '.join(words).lower()
    if any(key in name for key in MONO):
        return '#e4e4e0', '#202124', words
    color, ink = PALETTE[crc32(name.encode()) % len(PALETTE)]  # stable per film
    return color, ink, words


def add_canister(pixmap, label):
    result = pixmap.copy()
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    width,height = result.width(),result.height()
    scale = min(width/240,height/160)
    painter.translate(width-69*scale,height-116*scale)
    painter.scale(scale,scale)
    # A short strip, spool, and rounded metal canister.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0,0,0,65))
    painter.drawRoundedRect(QRectF(-2,9,66,106),8,8)
    painter.setBrush(QColor('#4a3423'))
    painter.drawRoundedRect(QRectF(-8,39,19,68),3,3)
    painter.setBrush(QColor('#d6c5a0'))
    for row in range(44,104,10):
        painter.drawRect(QRectF(-5,row,4,5))
    painter.setBrush(QColor('#202124'))
    painter.drawRoundedRect(QRectF(2,11,56,98),8,8)
    painter.setBrush(QColor('#55575a'))
    painter.drawRoundedRect(QRectF(20,1,20,14),3,3)
    painter.setPen(QPen(QColor('#939598'),1))
    painter.drawLine(8,18,51,18)
    color, ink, words = badge_style(label)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(4,27,52,68),3,3)
    painter.setPen(QColor(ink))
    painter.setFont(QFont('',8,QFont.Weight.Bold))
    painter.drawText(QRectF(6,30,48,15),Qt.AlignmentFlag.AlignCenter,'35 mm')
    painter.setFont(QFont('',7,QFont.Weight.Bold))
    name='\n'.join(words[:4])
    painter.drawText(QRectF(6,47,48,44),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,name)
    painter.setPen(QColor('#dddddd'))
    painter.setFont(QFont('',6))
    painter.drawText(QRectF(5,95,50,11),Qt.AlignmentFlag.AlignCenter,'APROX.')
    painter.end()
    return result
