import json
import numpy as np
from film_poc.services import preferences
from film_poc.ui.theme import THEMES
from film_poc.ui.theme import DEFAULT_THEME


def test_corrupt_or_unknown_theme_falls_back(tmp_path):
    folder=tmp_path/'library'
    folder.mkdir()
    for text in ('broken JSON','[]',json.dumps({'theme':'unknown'})):
        (folder/'appearance.json').write_text(text)
        assert preferences.load_theme(THEMES,DEFAULT_THEME)==DEFAULT_THEME


def test_theme_switch_persists_without_reprocessing(tmp_path,wait_window):
    from film_poc.ui import Window
    window=Window()
    window.gallery.look.setCurrentIndex(0)
    window.loaded(tmp_path/'test.arw',np.full((30,50,3),.2,dtype=np.float32))
    wait_window(window)
    revision=window.preview_revision
    pixels=[image.toImage() for image in window.pixmaps]
    reference=window.backdrop.ambient.cacheKey()
    window.theme_selector.setCurrentIndex(1)
    assert preferences.load_theme(THEMES,DEFAULT_THEME)=='glass'
    assert window.backdrop.theme=='glass'
    assert window.preview_revision==revision
    assert [image.toImage() for image in window.pixmaps]==pixels
    assert window.backdrop.ambient.cacheKey()==reference
    window.close()
    reopened=Window()
    assert reopened.theme_name=='glass'
    assert reopened.theme_selector.currentData()=='glass'
    wait_window(reopened)
    reopened.theme_selector.setCurrentIndex(0)
    assert preferences.load_theme(THEMES,DEFAULT_THEME)=='darkroom'
    reopened.close()


def test_stylesheet_assets_exist():
    from pathlib import Path
    from film_poc.ui.theme import stylesheet
    for theme in THEMES:
        assert Path(stylesheet(theme).split('url(')[1].split(')')[0]).is_file()
