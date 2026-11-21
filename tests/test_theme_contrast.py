import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtWidgets import QApplication

from film_poc.ui import Window
from film_poc.ui.theme import THEMES, palette, stylesheet
from film_poc.ui.viewer import SURROUNDS


def luminance(color):
    channels = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    r, g, b = (c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4 for c in channels)
    return .2126*r + .7152*g + .0722*b


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high+.05)/(low+.05)


@pytest.mark.parametrize('foreground, background, minimum', [
    ('ink', 'panel', 7), ('ink', 'field', 7), ('muted', 'panel', 4.5), ('muted', 'field', 4.5),
    ('primary_text', 'primary', 4.5), ('primary_text', 'primary_hover', 4.5),
    ('accent', 'panel', 3), ('groove', 'panel', 3), ('groove', 'field', 3)])
def test_workshop_palette_contrast(foreground, background, minimum):
    colors = palette('darkroom')
    assert contrast(colors[foreground], colors[background]) >= minimum


def test_workshop_surfaces_step_up_in_lightness_and_stay_neutral():
    colors = palette('darkroom')
    steps = [luminance(colors[k]) for k in ('window', 'panel', 'field')]
    assert steps == sorted(steps) and len(set(steps)) == 3
    for key in ('window', 'panel', 'field', 'edge'):
        r, g, b = (int(colors[key][i:i+2], 16) for i in (1, 3, 5))
        assert max(r, g, b) - min(r, g, b) <= 4  # no colour cast around the photo


@pytest.mark.parametrize('theme', THEMES)
def test_stylesheet_has_no_unresolved_tokens_or_missing_fonts(theme):
    css = stylesheet(theme)
    assert '$' not in css and 'Segoe UI' not in css


def test_viewer_surround_selector(wait_window):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    assert window.surround.count() == len(SURROUNDS)
    window.surround.setCurrentText('Negro')
    assert window.viewer.surround == SURROUNDS['Negro']
    window.viewer.set_surround('nonsense')
    assert window.viewer.surround == SURROUNDS['Negro']
    wait_window(window)
    window.close()
