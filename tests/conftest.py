import pytest


@pytest.fixture(autouse=True)
def isolated_user_library(monkeypatch,tmp_path):
    monkeypatch.setenv('FILM_POC_USER_DIR',str(tmp_path/'library'))
