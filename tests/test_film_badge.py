import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from film_poc.film_badge import add_canister


def test_canister_is_added_without_changing_reference():
    app=QApplication.instance() or QApplication([])
    original=QPixmap(240,160)
    original.fill()
    before=original.toImage()
    for name in ('Kodak Gold 200','Ilford HP5 Plus 400','Classic Chrome'):
        result=add_canister(original,name)
        assert result.size()==original.size()
        assert result.toImage()!=before
        assert original.toImage()==before
