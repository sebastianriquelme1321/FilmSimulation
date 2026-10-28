import numpy as np
from film_poc.engine import apply_look


def test_red_filter_favors_red_and_green_filter_favors_green():
    source=np.array([[[.7,.03,.03],[.03,.7,.03],[.03,.03,.7]]],dtype=np.float32)
    for base in ('ACROS','Monochrome'):
        red=apply_look(source,f'{base} + R (aproximación)')[0,:,0]
        green=apply_look(source,f'{base} + G (aproximación)')[0,:,0]
        assert red[0]>red[1]>red[2]
        assert green[1]>green[0]>green[2]
