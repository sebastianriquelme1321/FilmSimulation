"""Two desktop themes: matte darkroom and photo-lit glass. Neutral image viewers."""
from pathlib import Path
from string import Template

THEMES={'darkroom':'Cuarto oscuro','glass':'Vidrio y luz'}
DEFAULT_THEME='darkroom'


def stylesheet(theme):
    glass=theme=='glass'
    colors=dict(ink='#F2EDE4',muted='#B3AA9E',accent='#F28C38' if not glass else '#E9A23B',
                panel='rgba(22, 20, 18, 175)' if glass else '#1B1815',
                field='rgba(255,255,255,20)' if glass else '#211E19',
                edge='rgba(255,255,255,55)' if glass else '#3A342C',
                hover='rgba(255,255,255,30)' if glass else '#30281F',
                selected='rgba(233,162,59,28)' if glass else '#362617',
                radius='22' if glass else '9', control='18' if glass else '9',
                primary='#F7F7F5' if glass else '#F28C38',
                primary_hover='#FFFFFF' if glass else '#FF9C49',
                title_font='Georgia' if glass else 'Segoe UI',
                chevron=(Path(__file__).parent/'assets'/'icons'/'chevron.svg').as_posix())
    return Template(_CSS).substitute(colors)


_CSS = """
QMainWindow { background: #141210; }
QWidget { font-size: 13px; color: $ink; }
QWidget#root { background: transparent; }
QLabel { color: $ink; background: transparent; border: none; }
QLabel#brand { font-size: 25px; font-weight: 600; letter-spacing: -1px; }
QLabel#eyebrow { font-size: 10px; color: $muted; letter-spacing: 2px; }
QLabel#sectionTitle { font-family: '$title_font'; font-size: 20px; font-weight: 600; }
QLabel#muted { color: $muted; font-size: 12px; }
QLabel#count { color: $muted; font-size: 11px; padding: 4px 6px; }
QFrame#library { background: $panel; border: 1px solid $edge; border-radius: ${radius}px; }
QFrame#workspace { background: transparent; border: none; }
QFrame#photoFrame { background: #303030; border: 1px solid #393939; border-radius: 12px; }
QLabel#photoLabel { color: #E4E4E4; font-size: 10px; font-weight: 600; letter-spacing: 1px; }
QLabel#photoView { background: #303030; color: #C0C0C0; border: none; }
QLabel#details { color: $muted; font-size: 11px; padding-top: 9px; border-top: 1px solid $edge; }
QPushButton { background: $field; color: $ink; border: 1px solid $edge;
 border-radius: ${control}px; padding: 9px 14px; font-weight: 500; }
QPushButton:hover { background: $hover; border-color: $muted; }
QPushButton:pressed { background: $selected; }
QPushButton:focus { border: 1px solid $accent; }
QPushButton#primary { background: $primary; color: #141210; border: 1px solid $primary; font-weight: 600; }
QPushButton#primary:hover { background: $primary_hover; }
QPushButton#primary:disabled, QPushButton:disabled { color: #766F65; background: #25221E; border-color: #37322B; }
QLineEdit, QComboBox, QDoubleSpinBox { background: $field; color: $ink; border: 1px solid $edge;
 border-radius: ${control}px; padding: 8px 11px; selection-background-color: $accent; selection-color: #141210; }
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border-color: $accent; }
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled { color: #766F65; }
QComboBox { padding-right: 27px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url($chevron); width: 12px; height: 8px; }
QComboBox QAbstractItemView { background: #211E19; color: $ink; border: 1px solid $edge;
 selection-background-color: #473522; selection-color: $ink; outline: none; }
QDoubleSpinBox { padding: 6px; min-height: 20px; }
QDoubleSpinBox QLineEdit { border: none; background: transparent; padding: 0; }
QListWidget { background: transparent; border: none; color: $ink; padding: 0; outline: none; }
QListWidget::item { background: transparent; padding: 5px; border: 1px solid transparent; border-radius: ${radius}px; }
QListWidget::item:selected { background: $selected; border: 1px solid $accent; color: $ink; }
QListWidget::item:hover { background: $hover; border-color: $edge; }
QListWidget:focus::item:selected { border: 2px solid $accent; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 3px 0; }
QScrollBar::handle:vertical { background: #746C5E; min-height: 32px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: #746C5E; min-width: 32px; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QProgressBar { background: #302A22; border: none; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: $accent; }
QSplitter::handle { background: transparent; }
QToolTip { background: #211E19; color: $ink; border: 1px solid $edge; padding: 7px; }
QSlider::groove:horizontal { height: 4px; background: #514A40; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { background: $ink; border: 1px solid $accent; width: 14px; margin: -6px 0; border-radius: 7px; }
QSlider::handle:horizontal:focus { border: 2px solid $accent; }
QSlider::handle:horizontal:disabled { background: #766F65; border-color: #766F65; }
"""

STYLE=stylesheet(DEFAULT_THEME)
