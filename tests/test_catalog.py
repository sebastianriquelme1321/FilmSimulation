import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
from PySide6.QtWidgets import QApplication
from film_poc.catalog import metadata,filtered_names,origins,reference_thumbnails
from film_poc.engine import LOOKS
from film_poc.ui import Window


def test_origin_groups_cover_catalog_without_overlap():
    groups=[filtered_names(origin) for origin in origins()]
    assert sorted(name for group in groups for name in group)==sorted(LOOKS)
    assert len(filtered_names('darktable'))==5
    assert len(filtered_names('Personalizadas'))==6
    assert len(filtered_names('Todos los orígenes','kodak'))==5
    assert metadata('Kodak Gold 200 (película aproximada)')['origin']=='spektrafilm / Film Lab'


def test_filter_selection_search_empty_and_thumbnail_integrity(tmp_path):
    app=QApplication.instance() or QApplication([])
    window=Window()
    source=np.random.default_rng(19).random((40,60,3),dtype=np.float32)
    previews=reference_thumbnails()
    assert set(previews)==set(LOOKS)
    original_icons=[window.gallery.item(i).icon().cacheKey() for i in range(31)]
    window.loaded((tmp_path/'test.arw',source))
    window.set_busy(False)
    assert window.gallery.count()==31
    assert all(not window.gallery.item(i).icon().isNull() for i in range(31))
    # The pixel buffers used by every card stay fixed across photo imports.
    buffers={name: window.thumbs[name].cacheKey() for name in LOOKS}
    window.loaded((tmp_path/'second.arw',np.zeros_like(source)))
    assert buffers=={name: window.thumbs[name].cacheKey() for name in LOOKS}
    window.origin.setCurrentText('darktable')
    assert window.look.count()==window.gallery.count()==5
    window.gallery.setCurrentRow(2)
    assert window.look.currentText()==window.gallery.currentItem().data(256)
    window.search.setText('does-not-exist')
    assert window.gallery.count()==0 and not window.save_button.isEnabled()
    window.search.clear()
    window.origin.setCurrentIndex(0)
    window.search.setText('Gold 200')
    assert window.gallery.count()==1
    assert 'Gold 200' in window.look.currentText() and window.save_button.isEnabled()
    assert 'spektrafilm' in window.details.text()
    window.close()


def test_import_does_not_generate_cards(monkeypatch,tmp_path):
    from film_poc import ui
    source=np.zeros((3,4,3),dtype=np.float32)
    monkeypatch.setattr(ui,'decode',lambda path: source)
    path=tmp_path/'sample.arw'
    result=ui.load_photo(path)
    assert len(result)==2 and result[0]==path and result[1] is source
