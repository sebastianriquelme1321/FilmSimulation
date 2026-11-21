import importlib.metadata
import logging
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

import film_poc
from film_poc.adapters import logs
from film_poc.services import diagnostics

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def clean_logger():
    logger = logging.getLogger('film_poc')
    before = list(logger.handlers)
    yield logger
    for handler in list(logger.handlers):
        if handler not in before:
            logger.removeHandler(handler)
            handler.close()


def test_version_matches_pyproject_and_falls_back(monkeypatch):
    text = (ROOT/'pyproject.toml').read_text(encoding='utf-8')
    assert re.search(r'^version = "([^"]+)"', text, re.M).group(1) == film_poc.__version__

    def missing(_):
        raise importlib.metadata.PackageNotFoundError
    monkeypatch.setattr(importlib.metadata, 'version', missing)
    assert diagnostics.app_version() == film_poc.__version__


def test_system_info_is_free_of_personal_data():
    info = diagnostics.system_info('glass', '6.12.0')
    for needle in ('FilmSimulation', 'Python', 'PySide6', 'rawpy', 'LibRaw', '.arw', 'glass'):
        assert needle in info
    assert str(Path.home()) not in info
    assert Path.home().name not in info


def test_issue_url_encoding_and_templates():
    for kind, name in (('feedback', 'feedback.yml'), ('bug', 'bug_report.yml')):
        url = diagnostics.issue_url(kind, 'línea & = # ?\nsegunda')
        assert (ROOT/'.github'/'ISSUE_TEMPLATE'/name).exists()
        assert url.startswith(diagnostics.REPO_URL + '/issues/new?')
        assert ' ' not in url and '\n' not in url and '#' not in url
        query = parse_qs(urlsplit(url).query)
        assert query['template'] == [name]
        assert query['title'][0].startswith('[')
        assert 'FilmSimulation' in query['system'][0]
        assert query['log'] == ['línea & = # ?\nsegunda']


def test_issue_url_cap_keeps_system_info_and_newest_log():
    log = ''.join(f'line {i} ' + 'x' * 80 + '\n' for i in range(2000))
    url = diagnostics.issue_url('bug', log)
    assert len(url) < 7000
    query = parse_qs(urlsplit(url).query)
    assert query['system'][0].startswith('FilmSimulation')
    assert query['log'][0].rstrip().endswith('line 1999 ' + 'x' * 80)


def test_log_rotation_and_idempotent_setup(tmp_path, clean_logger):
    path = logs.setup_logging()
    assert path == tmp_path/'library'/'logs'/'film_poc.log' == logs.log_dir()/'film_poc.log'
    logs.setup_logging()
    mine = [h for h in clean_logger.handlers if getattr(h, '_film_poc', False)]
    assert len(mine) == 1
    handler = mine[0]
    assert (handler.maxBytes, handler.backupCount) == (512 * 1024, 2)
    assert handler.encoding == 'utf-8' and clean_logger.level == logging.INFO
    logging.getLogger('film_poc.test').info('hola ñandú')
    handler.flush()
    assert 'hola ñandú' in logs.tail_log() and 'INFO' in logs.tail_log()
    assert logs.tail_log(5) == logs.tail_log(100)[-5:]


def test_setup_follows_a_changed_user_dir(tmp_path, monkeypatch, clean_logger):
    logs.setup_logging()
    monkeypatch.setenv('FILM_POC_USER_DIR', str(tmp_path/'other'))
    logs.setup_logging()
    assert len([h for h in clean_logger.handlers if getattr(h, '_film_poc', False)]) == 1
    assert (tmp_path/'other'/'logs'/'film_poc.log').exists()


def test_tail_log_without_file():
    assert logs.tail_log() == ''


def test_excepthook_logs_notifies_and_chains(monkeypatch, clean_logger):
    logs.setup_logging()
    chained, notified = [], []
    monkeypatch.setattr(sys, 'excepthook', lambda *args: chained.append(args[0]))
    logs.install_excepthook(notified.append)
    try:
        raise ValueError('boom')
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert chained == [ValueError] and len(notified) == 1
    assert 'Uncaught exception' in logs.tail_log() and 'boom' in logs.tail_log()
    monkeypatch.setattr(sys, 'excepthook', lambda *args: None)
    logs.install_excepthook(lambda exc: 1 / 0)  # a failing notifier must not escape
    sys.excepthook(ValueError, ValueError('x'), None)
