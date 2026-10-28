import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6.QtWidgets import QApplication
from film_poc.ui import Window, Job


def test_window_render_and_background_job(tmp_path,wait_window):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.show()
    app.processEvents()
    assert not window.save_button.isEnabled()
    window.look.setCurrentIndex(0)
    window.loaded((tmp_path / 'synthetic.arw', np.full((100, 160, 3), .18, dtype=np.float32)))
    window.set_busy(False)
    assert window.save_button.isEnabled()
    wait_window(window)
    assert len(window.pixmaps) == 2
    assert all(not pixmap.isNull() for pixmap in window.pixmaps)
    assert window.look.count() == 31
    for index in range(window.look.count()):
        window.look.setCurrentIndex(index)
        assert all(not pixmap.isNull() for pixmap in window.pixmaps)
    received = []
    job = Job(lambda: 42, window)
    job.done.connect(received.append)
    job.start()
    assert job.wait(5000)
    app.processEvents()
    assert received == [42]
    wait_window(window)
    window.close()


def test_edit_controls_and_raw_export_route(tmp_path,monkeypatch,wait_window):
    import json
    import zipfile
    from film_poc import ui
    app=QApplication.instance() or QApplication([])
    window=Window()
    window.look.setCurrentIndex(0)
    source=tmp_path/'input.arw'
    source.write_bytes(b'original sensor bytes')
    window.loaded((source,np.full((30,40,3),.1,dtype=np.float32)))
    window.exposure_slider.setValue(80)
    assert window.exposure.value()==.8
    window.temperature.setValue(25)
    window.intensity.setValue(40)
    window.render()
    wait_window(window)
    assert len(window.pixmaps)==2
    output=tmp_path/'preserved.zip'
    monkeypatch.setattr(ui.QFileDialog,'getSaveFileName',lambda *args: (str(output),''))
    monkeypatch.setattr(window,'run_job',lambda operation,callback,message: callback(operation()))
    window.export_format.setCurrentIndex(1)
    window.save()
    with zipfile.ZipFile(output) as archive:
        recipe=json.loads(archive.read('edit.recipe.json'))
        assert recipe['strength']==.4 and recipe['exposure_ev']==.8
        assert recipe['temperature']==25
    window.reset_adjustments()
    assert window.adjustment_values()=={'exposure_ev':0,'temperature':0,'intensity':1}
    assert window.exposure_slider.value()==0
    window.render_timer.stop()
    wait_window(window)
    window.close()
