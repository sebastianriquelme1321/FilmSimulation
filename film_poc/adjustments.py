"""Small pre-look linear RGB corrections, relative to the decoded camera WB."""
import numpy as np


def validate(exposure_ev=0, temperature=0, intensity=1):
    values=(exposure_ev,temperature,intensity)
    if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and np.isfinite(x) for x in values):
        raise ValueError('Los ajustes deben ser números finitos.')
    if not -3<=exposure_ev<=3 or not -100<=temperature<=100 or not 0<=intensity<=1:
        raise ValueError('Ajustes fuera de rango: exposición ±3 EV, temperatura ±100 e intensidad 0–1.')


def apply_base(linear, exposure_ev=0, temperature=0):
    validate(exposure_ev,temperature)
    # Relative warm/cool RGB correction, not a Kelvin-calibrated sensor WB.
    shift=temperature/100
    gains=np.array([2**(.35*shift),1,2**(-.35*shift)],dtype=np.float32)
    gains/=gains @ np.array([.2126,.7152,.0722],dtype=np.float32)
    return np.clip(np.asarray(linear,dtype=np.float32)*gains*(2**exposure_ev),0,1)
