import json

import pytest

from film_poc.adapters import storage
from film_poc.services import preferences
from film_poc.ui.theme import DEFAULT_THEME, THEMES
from film_poc.ui.viewer import SURROUNDS


def appearance(tmp_path):
    return json.loads((tmp_path/'library'/'appearance.json').read_text())


def test_surround_round_trip_and_default():
    assert preferences.load_surround(SURROUNDS,'Gris')=='Gris'
    preferences.save_surround('Blanco',SURROUNDS)
    assert preferences.load_surround(SURROUNDS,'Gris')=='Blanco'


def test_old_theme_only_file_is_kept(tmp_path):
    folder=tmp_path/'library'
    folder.mkdir()
    (folder/'appearance.json').write_text(json.dumps({'theme':'glass'}))
    assert preferences.load_surround(SURROUNDS,'Gris')=='Gris'
    preferences.save_surround('Negro',SURROUNDS)
    assert appearance(tmp_path)=={'theme':'glass','surround':'Negro'}
    assert preferences.load_theme(THEMES,DEFAULT_THEME)=='glass'


def test_saving_theme_preserves_surround(tmp_path):
    preferences.save_surround('Negro',SURROUNDS)
    preferences.save_theme('glass',THEMES)
    assert appearance(tmp_path)=={'theme':'glass','surround':'Negro'}


def test_invalid_surround_falls_back(tmp_path):
    folder=tmp_path/'library'
    folder.mkdir()
    for text in ('broken','[]',json.dumps({'surround':'Rojo'}),json.dumps({'surround':3})):
        (folder/'appearance.json').write_text(text)
        assert preferences.load_surround(SURROUNDS,'Gris')=='Gris'
    with pytest.raises(ValueError):
        preferences.save_surround('Rojo',SURROUNDS)
    assert storage.load_surround_name() is None


def test_window_restores_and_saves_surround(tmp_path):
    from film_poc.ui import Window
    preferences.save_surround('Blanco',SURROUNDS)
    window=Window()
    assert window.surround.currentText()=='Blanco'
    assert window.viewer.surround==SURROUNDS['Blanco']
    window.surround.setCurrentText('Negro')
    assert appearance(tmp_path)['surround']=='Negro'
    window.close()


def test_surround_save_failure_is_ignored(monkeypatch):
    from film_poc.ui import Window
    window=Window()

    def fail(*_):
        raise OSError('read-only')
    monkeypatch.setattr('film_poc.ui.window.save_surround',fail)
    window.surround.setCurrentText('Blanco')
    assert window.viewer.surround==SURROUNDS['Blanco']
    window.close()


def test_export_shortcut_triggers_save(monkeypatch):
    from PySide6.QtGui import QKeySequence, QShortcut

    from film_poc.ui import Window
    calls=[]
    monkeypatch.setattr(Window,'save',lambda self:calls.append(1))
    window=Window()
    shortcuts=[s for s in window.findChildren(QShortcut) if s.key()==QKeySequence('Ctrl+E')]
    assert len(shortcuts)==1
    shortcuts[0].activated.emit()
    assert calls==[1]
    assert 'E' in window.save_button.toolTip()
    window.close()
