import numpy as np
import pytest

from film_poc.core import render as engine
from film_poc.core.looks.base import Look, LookRegistry
from film_poc.services.catalog import metadata


class Invert:
    def apply(self, linear, look):
        return (1 - engine.render_base(linear)).astype(np.float32)


@pytest.fixture
def fake():
    engine.LOOKS.add_backend('fake', Invert())
    engine.LOOKS['Fake'] = Look('Fake', 'fake', 'Tests', 'detail')
    yield 'Fake'
    del engine.LOOKS['Fake']
    del engine.LOOKS._backends['fake']


def test_register_get_and_order():
    reg = LookRegistry()
    reg['b'] = Look('B')
    reg['a'] = Look('A', 'x', params={'path': 'p'})
    assert 'a' in reg and list(reg) == ['b', 'a']
    assert reg['a'].params['path'] == 'p'
    assert [look.display_name for look in dict(reg).values()] == ['B', 'A']


def test_unknown_names_and_backends():
    with pytest.raises(KeyError):
        engine.LOOKS['nope']
    with pytest.raises(ValueError):
        LookRegistry().backend(Look('X', 'ghost'))


def test_new_backend_needs_no_other_module_changes(fake):
    linear = np.full((2, 2, 3), .2, np.float32)
    out = engine.apply_look(linear, fake)
    np.testing.assert_allclose(out, 1 - engine.render_base(linear), atol=1e-6)
    assert metadata(fake)['origin'] == 'Tests'
    assert engine.look_slug(fake) == 'fake'
    engine.render_edit(linear, fake, exposure_ev=.5)
