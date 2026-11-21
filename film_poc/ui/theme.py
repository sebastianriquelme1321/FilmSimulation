"""Two desktop themes: neutral gray workshop and photo-lit glass. Neutral image viewers."""
from pathlib import Path
from string import Template

THEMES={'darkroom':'Taller neutro','glass':'Vidrio y luz'}
DEFAULT_THEME='darkroom'
CHEVRON=(Path(__file__).parents[1]/'assets'/'icons'/'chevron.svg').as_posix()

# Neutral grays in steps (window < panel < field): hierarchy without colour casts that would
# bias how the photo is judged. One accent, used for selection and focus only.
_COMMON=dict(radius='9', control='9', title_family='', eyebrow_tracking='0px', chevron=CHEVRON)
PALETTES={
    'darkroom':dict(_COMMON, window='#1B1B1D', panel='#252527', field='#2F2F32', edge='#3E3E42',
                    hover='#38383C', selected='#22344D', ink='#F0F0F2', muted='#B0B0B6',
                    accent='#4C8DF6', primary='#2F6FDB', primary_hover='#2C6AD6',
                    primary_text='#FFFFFF', groove='#85858C', dis_text='#74747A',
                    dis_bg='#2A2A2D', dis_edge='#38383C', combo_sel='#27406A', scroll='#77777E',
                    prog='#303034'),
    'glass':dict(_COMMON, window='#0D0E11', panel='rgba(22, 20, 18, 175)',
                 field='rgba(255,255,255,20)', edge='rgba(255,255,255,55)',
                 hover='rgba(255,255,255,30)', selected='rgba(233,162,59,28)', ink='#F2EDE4',
                 muted='#B3AA9E', accent='#E9A23B', primary='#F7F7F5', primary_hover='#FFFFFF',
                 primary_text='#141210', groove='#7A7062', dis_text='#766F65', dis_bg='#25221E',
                 dis_edge='#37322B', combo_sel='#473522', scroll='#746C5E', prog='#302A22',
                 radius='22', control='18', title_family="font-family: 'Georgia';"),
}


def palette(theme):
    """Colour tokens of a theme (window, panel, ink, accent, ...)."""
    return PALETTES[theme]


def stylesheet(theme):
    return Template(_CSS).substitute(PALETTES[theme])


_CSS = """
QMainWindow { background: $window; }
QWidget { font-size: 13px; color: $ink; }
QWidget#root { background: transparent; }
QLabel { color: $ink; background: transparent; border: none; }
QLabel#brand { font-size: 25px; font-weight: 600; letter-spacing: -1px; }
QLabel#eyebrow { font-size: 12px; color: $muted; letter-spacing: $eyebrow_tracking; }
QLabel#sectionTitle { $title_family font-size: 20px; font-weight: 600; }
QLabel#muted { color: $muted; font-size: 12px; }
QLabel#count { color: $muted; font-size: 12px; padding: 4px 6px; }
QFrame#library { background: $panel; border: 1px solid $edge; border-radius: ${radius}px; }
QFrame#workspace { background: transparent; border: none; }
QLabel#details { color: $muted; font-size: 12px; padding-top: 9px; border-top: 1px solid $edge; }
QPushButton { background: $field; color: $ink; border: 1px solid $edge;
 border-radius: ${control}px; padding: 9px 14px; font-weight: 500; }
QPushButton:hover { background: $hover; border-color: $muted; }
QPushButton:pressed { background: $selected; }
QPushButton:focus { border: 1px solid $accent; }
QPushButton#tool { padding: 5px 11px; font-size: 12px; }
QPushButton#tool:checked { background: $selected; border-color: $accent; }
QLabel#value { color: $muted; }
QPushButton#primary { background: $primary; color: $primary_text; border: 1px solid $primary; font-weight: 600; }
QPushButton#primary:hover { background: $primary_hover; }
QPushButton#primary:disabled, QPushButton:disabled { color: $dis_text; background: $dis_bg; border-color: $dis_edge; }
QLineEdit, QComboBox, QDoubleSpinBox { background: $field; color: $ink; border: 1px solid $edge;
 border-radius: ${control}px; padding: 8px 11px; selection-background-color: $accent; selection-color: $primary_text; }
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border-color: $accent; }
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled { color: $dis_text; }
QComboBox { padding-right: 27px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url($chevron); width: 12px; height: 8px; }
QComboBox QAbstractItemView { background: $field; color: $ink; border: 1px solid $edge;
 selection-background-color: $combo_sel; selection-color: $ink; outline: none; }
QDoubleSpinBox { padding: 6px; min-height: 20px; }
QDoubleSpinBox QLineEdit { border: none; background: transparent; padding: 0; }
QListWidget { background: transparent; border: none; color: $ink; padding: 0; outline: none; }
QListWidget::item { background: transparent; padding: 5px; border: 1px solid transparent; border-radius: ${radius}px; }
QListWidget::item:selected { background: $selected; border: 2px solid $accent; padding: 4px; color: $ink; }
QListWidget::item:hover { background: $hover; border-color: $edge; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 3px 0; }
QScrollBar::handle:vertical { background: $scroll; min-height: 32px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: $scroll; min-width: 32px; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QProgressBar { background: $prog; border: none; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: $accent; }
QSplitter::handle { background: transparent; }
QToolTip { background: $field; color: $ink; border: 1px solid $edge; padding: 7px; }
QSlider::groove:horizontal { height: 4px; background: $groove; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { background: $ink; border: 1px solid $accent; width: 14px; margin: -6px 0; border-radius: 7px; }
QSlider::handle:horizontal:focus { border: 2px solid $accent; }
QSlider::handle:horizontal:disabled { background: $dis_text; border-color: $dis_text; }
"""

STYLE=stylesheet(DEFAULT_THEME)
