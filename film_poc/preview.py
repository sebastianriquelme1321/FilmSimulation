"""Bounded single-preview cache. Owned and used by one preview worker at a time."""
import numpy as np

from . import adjustments, engine
from .grain import apply_grain


class PreviewPipeline:
    def __init__(self) -> None:
        self.source = None
        self.base_key = None
        self.look_key = None
        self.mix_key = None

    def render(self, source: np.ndarray, name: str | None, exposure_ev: float = 0,
               temperature: float = 0, intensity: float = 1, grain: str = 'Desactivado',
               step: int = 1) -> tuple[np.ndarray, np.ndarray | None]:
        """Return (before8, after8); after8 is None when name is None. Reuses unchanged stages."""
        if name is None:
            adjustments.validate(exposure_ev, temperature, intensity)
            base_name = None
            values = {'exposure_ev': exposure_ev, 'temperature': temperature,
                      'intensity': intensity}
        else:
            base_name, values = engine.edit_settings(name, exposure_ev, temperature, intensity)
        base_key = (values['exposure_ev'], values['temperature'])
        if source is not self.source or base_key != self.base_key:
            self.source = source
            self.base_key = base_key
            self.corrected = adjustments.apply_base(source, *base_key)
            self.before = engine.render_base(self.corrected)
            self.before8 = engine.uint8(self.before)
            self.look_key = None
            self.mix_key = None
        if name is None:
            return self.before8, None
        amount = values['intensity']
        if amount == 0:
            mixed = self.before
        else:
            if base_name != self.look_key:
                self.look = engine.apply_look(self.corrected, base_name)
                self.look_key = base_name
                self.mix_key = None
            if self.mix_key != (base_name, amount):
                self.mixed = np.clip(self.before*(1-amount) + self.look*amount,
                                     0, 1).astype(np.float32)
                self.mix_key = (base_name, amount)
            mixed = self.mixed
        return self.before8, engine.uint8(apply_grain(mixed, grain, step=step))
