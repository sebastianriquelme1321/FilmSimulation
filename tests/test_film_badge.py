import os

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from film_poc.core.render import LOOKS
from film_poc.services.catalog import metadata
from film_poc.ui.film_badge import BRANDS, add_canister, badge_style


def test_canister_is_added_without_changing_reference():
    QApplication.instance() or QApplication([])
    original=QPixmap(240,160)
    original.fill()
    before=original.toImage()
    for name in ('Kodak Gold 200','Ilford HP5 Plus 400','Classic Chrome'):
        result=add_canister(original,name)
        assert result.size()==original.size()
        assert result.toImage()!=before
        assert original.toImage()==before


def test_badges_carry_no_brand_names_and_are_stable():
    seen = {}
    for name in LOOKS:
        label = metadata(name)['label']
        color, ink, words = badge_style(label)
        assert not {w.lower() for w in words} & set(BRANDS), label
        assert badge_style(label) == (color, ink, words)  # deterministic across calls
        assert words, label
        seen[label] = color
    assert len(set(seen.values())) > 2  # films are told apart by colour, not by brand
    assert badge_style('Ilford HP5 Plus 400')[2] == ['HP5', 'Plus', '400']
    assert badge_style('Kodak Kodachrome 64')[2] == ['Koda', 'chrome', '64']
