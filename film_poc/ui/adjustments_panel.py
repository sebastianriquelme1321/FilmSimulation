"""Exposure, temperature, intensity and colour controls with one `changed` signal."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class AdjustmentsPanel(QWidget):
    """The edit controls, one per row (name and value above, slider below)."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        controls = QVBoxLayout(self)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)

        self.exposure = QDoubleSpinBox()
        self.exposure.setRange(-3, 3)
        self.exposure.setDecimals(2)
        self.exposure.setSingleStep(.1)
        self.exposure.setSuffix(' EV')
        self.exposure.setAccessibleName('Exposición antes de la simulación')
        self.exposure.setKeyboardTracking(False)
        self.exposure.setFixedWidth(104)
        self.exposure.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.exposure.setToolTip('Escribe un valor exacto entre −3 y +3 EV y pulsa Enter.')
        self.exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self.exposure_slider.setRange(-300, 300)
        self.exposure_slider.setSingleStep(10)
        self.exposure_slider.setPageStep(50)
        self.exposure_slider.setAccessibleName('Deslizador de exposición en EV')
        self.exposure_slider.setToolTip(
            'Arrastra para aclarar u oscurecer. Flechas: 0,1 EV; RePág/AvPág: 0,5 EV.')
        controls.addLayout(self._row('Exposición', self.exposure))
        controls.addWidget(self.exposure_slider)
        controls.addSpacing(8)

        self.temperature = QSlider(Qt.Orientation.Horizontal)
        self.temperature.setRange(-100, 100)
        self.temperature.setAccessibleName('Temperatura relativa: frío a cálido')
        self.temperature.setToolTip('Corrección RGB relativa al balance de cámara; '
                                    'no es una temperatura calibrada en Kelvin.')
        self.temperature_label = QLabel('0')
        self.temperature_label.setObjectName('value')
        controls.addLayout(self._row('Temperatura', self.temperature_label))
        controls.addWidget(self.temperature)
        controls.addSpacing(8)

        self.intensity = QSlider(Qt.Orientation.Horizontal)
        self.intensity.setRange(0, 100)
        self.intensity.setValue(100)
        self.intensity.setAccessibleName('Intensidad de la simulación en porcentaje')
        self.intensity_label = QLabel('100 %')
        self.intensity_label.setObjectName('value')
        controls.addLayout(self._row('Intensidad del look', self.intensity_label))
        controls.addWidget(self.intensity)
        controls.addSpacing(8)

        section = QLabel('Color')
        section.setObjectName('muted')
        controls.addWidget(section)
        self.contrast, self.contrast_label = self._signed_slider(
            controls, 'Contraste', 'Contraste: plano a marcado',
            'Aplana o endurece el contraste alrededor del gris medio.')
        self.saturation, self.saturation_label = self._signed_slider(
            controls, 'Saturación', 'Saturación: apagado a intenso',
            'Apaga o intensifica los colores.')
        self.tint, self.tint_label = self._signed_slider(
            controls, 'Tinte', 'Tinte: verde a magenta', 'Verde ← → magenta')
        controls.addSpacing(2)

        self.reset_button = QPushButton('Restablecer ajustes')
        self.reset_button.setToolTip(
            'Restablece todos los ajustes; mantiene la película y el grano.')
        controls.addWidget(self.reset_button)

        for figures in (self.exposure, self.temperature_label, self.intensity_label,
                        self.contrast_label, self.saturation_label, self.tint_label):
            font = figures.font()
            font.setFeature(QFont.Tag('tnum'), 1)  # tabular figures: values do not jitter
            figures.setFont(font)
        for control in (self.exposure, self.temperature, self.intensity, self.contrast,
                        self.saturation, self.tint):
            control.valueChanged.connect(self._changed)
        self.exposure_slider.valueChanged.connect(lambda value: self.exposure.setValue(value / 100))
        self.reset_button.clicked.connect(self.reset)
        self._sync()

    def _signed_slider(self, layout, name, accessible, tooltip):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)
        slider.setAccessibleName(accessible)
        slider.setToolTip(tooltip)
        label = QLabel('+0')
        label.setObjectName('value')
        layout.addLayout(self._row(name, label))
        layout.addWidget(slider)
        return slider, label

    @staticmethod
    def _row(name, value_widget):
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(name))
        row.addStretch()
        row.addWidget(value_widget)
        return row

    def values(self):
        """Current settings as engine keyword arguments."""
        return {'exposure_ev': self.exposure.value(), 'temperature': self.temperature.value(),
                'intensity': self.intensity.value() / 100, 'contrast': self.contrast.value(),
                'saturation': self.saturation.value(), 'tint': self.tint.value()}

    def reset(self):
        """Back to neutral: 0 EV, no colour changes, full look intensity."""
        self.exposure.setValue(0)
        for slider in (self.temperature, self.contrast, self.saturation, self.tint):
            slider.setValue(0)
        self.intensity.setValue(100)

    def set_values(self, exposure_ev, temperature, intensity, contrast=0, saturation=0, tint=0):
        """Load settings (intensity as a 0-1 fraction) without emitting `changed`."""
        controls = ((self.exposure, exposure_ev), (self.temperature, int(temperature)),
                    (self.intensity, round(intensity * 100)), (self.contrast, int(contrast)),
                    (self.saturation, int(saturation)), (self.tint, int(tint)))
        for control, value in controls:
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        self._sync()

    def set_editable(self, editable):
        """Enable or disable every control (the labels stay as they are)."""
        for control in (self.exposure, self.exposure_slider, self.temperature,
                        self.intensity, self.contrast, self.saturation, self.tint,
                        self.reset_button):
            control.setEnabled(editable)

    def _sync(self):
        self.exposure_slider.blockSignals(True)
        self.exposure_slider.setValue(round(self.exposure.value() * 100))
        self.exposure_slider.blockSignals(False)
        self.temperature_label.setText(f'{self.temperature.value():+d}')
        self.intensity_label.setText(f'{self.intensity.value()} %')
        for slider, label in ((self.contrast, self.contrast_label),
                              (self.saturation, self.saturation_label),
                              (self.tint, self.tint_label)):
            label.setText(f'{slider.value():+d}')

    def _changed(self, *_):
        self._sync()
        self.changed.emit()
