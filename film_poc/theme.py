"""Warm film-studio palette with soft glass-like surfaces, portable Qt styles."""
from pathlib import Path

STYLE = """
QMainWindow, QWidget#root { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #f2ede2,stop:1 #e7e7e0); color: #292b28; }
QWidget { font-size: 13px; }
QLabel { color: #292b28; background: transparent; border: none; }
QLabel#brand { font-size: 30px; font-weight: 700; letter-spacing: -1px; }
QLabel#eyebrow { font-size: 10px; font-weight: 600; color: #80704d; letter-spacing: 2px; }
QLabel#sectionTitle { font-size: 19px; font-weight: 600; }
QLabel#muted { color: #797b72; font-size: 12px; }
QLabel#count { background: #e9e3d6; color: #766748; border-radius: 10px; padding: 4px 9px; font-size: 11px; }
QFrame#library { background: rgba(255, 253, 247, 220); border: 1px solid #fffdf8; border-radius: 23px; }
QFrame#workspace { background: rgba(255, 255, 255, 170); border: 1px solid #fffdf8; border-radius: 23px; }
QFrame#photoFrame { background: #323432; border: 1px solid #41433f; border-radius: 16px; }
QLabel#photoLabel { color: #c8c9c2; font-size: 10px; font-weight: 600; letter-spacing: 1px; }
QLabel#photoView { background: #323432; color: #b5b7b0; font-size: 13px; border: none; }
QLabel#details { color: #65675e; font-size: 11px; padding-top: 9px; border-top: 1px solid #e6e3d9; }
QPushButton { background: rgba(255,255,255,205); color: #393a33; border: 1px solid #deddd3;
 border-radius: 17px; padding: 9px 15px; font-weight: 500; }
QPushButton:hover { background: #fffdf5; border-color: #c3b48f; }
QPushButton:pressed { background: #e7dfcc; }
QPushButton:focus { border: 2px solid #a17423; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f3cd65,stop:1 #eab94b);
 color: #483812; border: 1px solid #d3a940; font-weight: 600; }
QPushButton#primary:hover { background: #f8d77b; }
QPushButton#primary:disabled, QPushButton:disabled { color: #a7a69b; background: #e9e7de; border-color: #e1dfd5; }
QLineEdit, QComboBox { background: rgba(255,255,255,200); color: #41433a; border: 1px solid #deded4;
 border-radius: 13px; padding: 9px 12px; selection-background-color: #e8c26c; selection-color: #292b28; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #b89443; background: #fffef9; }
QLineEdit:disabled, QComboBox:disabled { color: #a7a69b; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down { border: none; width: 23px; }
QComboBox::down-arrow { image: url(__CHEVRON__); width: 12px; height: 8px; }
QComboBox QAbstractItemView { background: #fffdf7; color: #34362e; border: 1px solid #d7cdb6;
 selection-background-color: #f0dfb7; selection-color: #34362e; outline: none; }
QListWidget { background: transparent; border: none; color: #42443b; padding: 0; outline: none; }
QListWidget::item { background: #f4f2e9; padding: 5px; border: 1px solid #e5e2d7; border-radius: 13px; }
QListWidget::item:selected { background: #f6e7bf; border: 1px solid #b78b31; color: #594318; }
QListWidget::item:hover { background: #f9f3df; border-color: #b9ab8a; }
QListWidget:focus::item:selected { border: 2px solid #a17423; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 3px 0; }
QScrollBar::handle:vertical { background: #cbc7b9; min-height: 32px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QProgressBar { background: #e1ddcf; border: none; border-radius: 3px; max-height: 4px; }
QProgressBar::chunk { background: #c3993e; border-radius: 3px; }
QSplitter::handle { background: transparent; }
QToolTip { background: #fffdf4; color: #33362e; border: 1px solid #cbbf9f; padding: 7px; }
"""

STYLE = STYLE.replace("__CHEVRON__", (Path(__file__).parent / "assets" / "icons" / "chevron.svg").as_posix())

STYLE += """
QDoubleSpinBox { background: #fffdf7; color: #41433a; border: 1px solid #deded4; border-radius: 10px; padding: 6px; min-height: 20px; }
QSlider::groove:horizontal { height: 5px; background: #d9d6cb; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #b88b35; border-radius: 2px; }
QSlider::handle:horizontal { background: #fffdf7; border: 1px solid #b88b35; width: 15px; margin: -6px 0; border-radius: 8px; }
QSlider::handle:horizontal:focus { border: 2px solid #7b5c24; }
QSlider::handle:horizontal:disabled { border-color: #aaa; background: #ddd; }
"""

STYLE += "QDoubleSpinBox QLineEdit { border: none; background: transparent; padding: 0; }"
