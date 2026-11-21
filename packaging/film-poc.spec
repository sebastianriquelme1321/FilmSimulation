# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller --noconfirm packaging/film-poc.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent
IS_MAC = sys.platform == 'darwin'

# Package-layout independent: everything under film_poc is collected.
hiddenimports = collect_submodules('film_poc') + ['rawpy', 'scipy.interpolate']
datas = collect_data_files('film_poc')  # assets/**, darktable_*.json, ...
# Some modules read their own source (e.g. darktable_look.py hashes __file__ for its cache
# key), so ship the .py sources next to the compiled modules.
datas += collect_data_files('film_poc', include_py_files=True, excludes=['**/__pycache__'])

EXCLUDES = [
    # unittest/doctest/pydoc are needed by numpy.testing and scipy: do not exclude.
    'tkinter', 'pytest', 'test', 'tests', 'setuptools',
    'pip', 'distutils', 'lib2to3', 'IPython', 'matplotlib',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick',
    'PySide6.QtQml', 'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtNetwork',
    'PySide6.QtSql', 'PySide6.QtPdf', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.QtBluetooth', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtTest',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'scipy.stats', 'scipy.io', 'scipy.cluster', 'scipy.signal',
]

a = Analysis(
    [str(ROOT / 'packaging' / 'entry.py')],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='FilmSimulation',
    console=False,
    upx=False,
    strip=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='FilmSimulation', upx=False, strip=False)

if IS_MAC:
    app = BUNDLE(
        coll,
        name='FilmSimulation.app',
        bundle_identifier='com.filmsimulation.app',
        info_plist={
            'CFBundleName': 'FilmSimulation',
            'CFBundleDisplayName': 'FilmSimulation',
            'CFBundleShortVersionString': '0.6.0',
            'NSHighResolutionCapable': True,
        },
    )
