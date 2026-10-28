"""Shared high-contrast desktop theme with system fonts on Windows/macOS."""
STYLE='''
QMainWindow, QWidget#root { background: #171a1d; color: #ece7de; }
QWidget { font-size: 13px; }
QLabel { color: #e5e0d8; background: transparent; }
QLabel#muted { color: #a3aaa9; }
QPushButton { background: #30363a; color: #eee9df; border: 1px solid #4d5558;
 border-radius: 7px; padding: 8px 15px; }
QPushButton:hover { background: #414a4e; }
QPushButton#primary { background: #d0a658; color: #171a1d; border-color: #d0a658; font-weight: bold; }
QPushButton:disabled { color: #777e81; background: #24292c; border-color: #333b3e; }
QLineEdit, QComboBox { background: #252b2f; color: #eee9df; border: 1px solid #465056;
 border-radius: 6px; padding: 7px; selection-background-color: #9d7d43; }
QComboBox QAbstractItemView { background: #252b2f; color: #eee9df; selection-background-color: #5e5036; }
QListWidget { background: #1d2226; border: none; color: #ddd8d0; padding: 4px; }
QListWidget::item { background: #282e32; padding: 5px; border: 1px solid #3e474c; border-radius: 7px; }
QListWidget::item:selected { background: #4b4030; border: 2px solid #d0a658; color: white; }
QListWidget::item:hover { border-color: #858b88; }
QProgressBar { background: #252b2f; border: none; border-radius: 3px; max-height: 5px; }
QProgressBar::chunk { background: #d0a658; }
QSplitter::handle { background: #252b2f; width: 5px; }
'''
