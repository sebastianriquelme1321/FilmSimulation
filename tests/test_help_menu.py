import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from film_poc.services import diagnostics
from film_poc.ui import window as window_module
from film_poc.ui.about import DISCLAIMER, AboutDialog
from film_poc.ui.window import Window


@pytest.fixture
def window(wait_window):
    QApplication.instance() or QApplication([])
    win = Window()
    yield win
    wait_window(win)
    win.close()


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: urls.append(url) or True)
    return urls


def test_help_menu_lists_every_action(window):
    assert window.help_menu.title() == 'Ayuda'
    assert list(window.help_actions) == [
        'Enviar feedback…', 'Reportar un problema…', 'Copiar información del sistema',
        'Abrir carpeta de registros', 'Acerca de FilmSimulation']


def test_feedback_and_bug_open_prefilled_urls(window, opened):
    window.help_actions['Enviar feedback…'].trigger()
    window.help_actions['Reportar un problema…'].trigger()
    feedback, bug = (url.toString() for url in opened)
    assert 'template=feedback.yml' in feedback
    assert 'template=bug_report.yml' in bug and len(bug) < 7000


def test_copy_system_info(window, monkeypatch):
    copied = []
    monkeypatch.setattr(QApplication.clipboard(), 'setText', copied.append, raising=False)
    window.help_actions['Copiar información del sistema'].trigger()
    assert copied and copied[0].startswith('FilmSimulation')
    assert 'copiada' in window.status.text()


def test_open_log_folder(window, opened):
    window.help_actions['Abrir carpeta de registros'].trigger()
    assert opened == [QUrl.fromLocalFile(str(diagnostics.log_dir()))]
    assert diagnostics.log_dir().is_dir()


def test_about_dialog_content(window, monkeypatch, tmp_path):
    shown = []
    monkeypatch.setattr(AboutDialog, 'exec', lambda self: shown.append(self))
    window.help_actions['Acerca de FilmSimulation'].trigger()
    assert len(shown) == 1
    text = ' '.join(label.text() for label in shown[0].findChildren(QLabel))
    assert diagnostics.app_version() in text and 'GPL-3.0' in text
    assert 'THIRD_PARTY_NOTICES.md' in text and diagnostics.REPO_URL in text
    assert DISCLAIMER in text.replace('<b>', '') or 'sin afiliación ni respaldo' in text
    assert 'no envía datos' in text


def test_error_is_logged(window, monkeypatch, caplog):
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    with caplog.at_level('ERROR', logger='film_poc'):
        window.error('algo falló')
    assert 'algo falló' in caplog.text


def test_crash_dialog_only_with_an_application(monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: shown.append(args))
    QApplication.instance() or QApplication([])
    window_module.report_crash(ValueError('x'))
    assert 'Reportar un problema' in shown[0][2]
    monkeypatch.setattr(QApplication, 'instance', staticmethod(lambda: None))
    window_module.report_crash(ValueError('x'))
    assert len(shown) == 1
