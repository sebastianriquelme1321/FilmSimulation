from film_poc.adapters.storage import library_dir
from film_poc.ui import Window


def test_corrupt_library_entry_is_reported_in_status():
    root = library_dir()
    root.mkdir(parents=True, exist_ok=True)
    (root/'0123abcd.entry.json').write_text('[]')
    window = Window()
    assert window.status.text() == '1 entrada(s) de tu biblioteca no se pudieron cargar.'
    assert '0123abcd.entry.json' in window.status.toolTip()


def test_clean_library_shows_no_warning():
    window = Window()
    assert 'biblioteca' not in window.status.text()
    assert window.status.toolTip() == ''
