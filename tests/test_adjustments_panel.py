import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from film_poc.ui.adjustments_panel import AdjustmentsPanel

NEUTRAL = {'exposure_ev': 0, 'temperature': 0, 'intensity': 1.0,
           'contrast': 0, 'saturation': 0, 'tint': 0}


def panel():
    QApplication.instance() or QApplication([])
    return AdjustmentsPanel()


def test_values_always_include_all_keys_neutral():
    assert panel().values() == NEUTRAL


def test_color_sliders_range_and_signed_labels():
    p = panel()
    for slider, label in ((p.contrast, p.contrast_label), (p.saturation, p.saturation_label),
                          (p.tint, p.tint_label)):
        assert (slider.minimum(), slider.maximum()) == (-100, 100)
        assert label.text() == '+0'
    p.contrast.setValue(25)
    p.saturation.setValue(-40)
    p.tint.setValue(-3)
    assert (p.contrast_label.text(), p.saturation_label.text(), p.tint_label.text()) == (
        '+25', '-40', '-3')
    assert p.values()['saturation'] == -40
    assert 'magenta' in p.tint.toolTip()


def test_changed_emitted_by_color_sliders_and_reset_zeroes_them():
    p = panel()
    hits = []
    p.changed.connect(lambda: hits.append(1))
    p.tint.setValue(10)
    assert hits
    p.contrast.setValue(5)
    p.saturation.setValue(6)
    p.exposure.setValue(1)
    p.reset()
    assert p.values() == NEUTRAL
    assert p.tint_label.text() == '+0'


def test_set_values_is_silent_and_defaults_new_keys():
    p = panel()
    hits = []
    p.changed.connect(lambda: hits.append(1))
    p.set_values(.5, 10, .8, 20, -30, 40)
    assert not hits
    assert p.values() == {'exposure_ev': .5, 'temperature': 10, 'intensity': .8,
                          'contrast': 20, 'saturation': -30, 'tint': 40}
    assert p.contrast_label.text() == '+20'
    p.set_values(0, 0, 1)
    assert (p.contrast.value(), p.saturation.value(), p.tint.value()) == (0, 0, 0)


def test_set_editable_covers_color_sliders():
    p = panel()
    p.set_editable(False)
    assert not any(c.isEnabled() for c in (p.contrast, p.saturation, p.tint, p.reset_button))
    p.set_editable(True)
    assert all(c.isEnabled() for c in (p.contrast, p.saturation, p.tint))
