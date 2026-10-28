import numpy as np
from film_poc import engine, adjustments
from film_poc.preview import PreviewPipeline
from film_poc.grain import apply_grain


def test_cached_preview_matches_export_and_reuses_look(monkeypatch):
    calls=[]
    original=engine.apply_look
    def record(*args):
        calls.append(args[1])
        return original(*args)
    monkeypatch.setattr(engine,'apply_look',record)
    source=np.random.default_rng(5).random((24,35,3),dtype=np.float32)*.6
    name=next(iter(engine.LOOKS))
    pipeline=PreviewPipeline()
    for amount,grain in ((1,'Desactivado'),(.4,'Suave'),(.4,'Fuerte'),(0,'Desactivado')):
        images=pipeline.render(source,name,.3,-15,amount,grain,step=4)
        # Reference uses the production export path, without touching the cache.
        base=adjustments.apply_base(source,.3,-15)
        before=engine.render_base(base)
        after=np.clip(before*(1-amount)+original(base,name)*amount,0,1).astype(np.float32)
        np.testing.assert_array_equal(images[0],engine.uint8(before))
        np.testing.assert_array_equal(images[1],engine.uint8(apply_grain(after,grain,step=4)))
    assert calls==[name]
    pipeline.render(source,name,.4,-15,1)
    pipeline.render(source.copy(),name,.4,-15,1)
    assert calls==[name,name,name]


def test_latest_preview_wins_without_blocking_ui(tmp_path,monkeypatch,wait_window):
    import threading
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from film_poc.ui import Window
    app=QApplication.instance() or QApplication([])
    window=Window()
    wait_window(window)
    entered=threading.Event()
    release=threading.Event()
    calls=[]
    def slow(source,name,**values):
        calls.append(values['intensity'])
        if len(calls)==1:
            entered.set()
            assert release.wait(5)
        pixels=np.full(source.shape,round(values['intensity']*255),dtype=np.uint8)
        return pixels,pixels
    monkeypatch.setattr(window.preview_pipeline,'render',slow)
    window.loaded((tmp_path/'input.arw',np.full((20,30,3),.1,dtype=np.float32)))
    assert entered.wait(3)
    for value in (20,30,40):
        window.intensity.setValue(value)
        window.render()
    # The blocked worker has not prevented UI selection or queued 3 jobs.
    assert window.intensity.value()==40 and len(calls)==1
    release.set()
    wait_window(window)
    assert calls==[1,.4]
    assert window.pixmaps[1].toImage().pixelColor(0,0).red()==102
    window.close()


def test_bad_disk_cache_is_rebuilt(tmp_path):
    from film_poc.cache import cached_array
    calls=[]
    def build():
        calls.append(1)
        return np.ones((2,3),dtype=np.float32)
    cached_array('test','key',build,(2,3))
    np.testing.assert_array_equal(cached_array('test','key',build,(2,3)),np.ones((2,3)))
    assert len(calls)==1
    path=next((tmp_path/'library'/'cache'/'test').glob('*.npy'))
    path.write_bytes(b'corrupt cache')
    cached_array('test','key',build,(2,3))
    assert len(calls)==2


def test_browsing_filters_does_not_apply_any_look(tmp_path,wait_window):
    from PySide6.QtWidgets import QApplication
    from film_poc.ui import Window
    app=QApplication.instance() or QApplication([])
    window=Window()
    window.loaded((tmp_path/'test.arw',np.full((20,30,3),.1,dtype=np.float32)))
    wait_window(window)
    revision=window.preview_revision
    assert window.active_look is None and window.pixmaps[1] is None
    window.origin.setCurrentText('darktable')
    window.search.setText('chrome')
    window.gallery.setCurrentRow(0)
    assert window.preview_revision==revision and window.active_look is None
    window.gallery.itemActivated.emit(window.gallery.currentItem())
    wait_window(window)
    active=window.active_look
    revision=window.preview_revision
    window.search.clear()
    window.origin.setCurrentIndex(0)
    window.search.setText('Gold')
    assert window.active_look==active and window.preview_revision==revision
    assert window.save_button.isEnabled()
    window.close()
