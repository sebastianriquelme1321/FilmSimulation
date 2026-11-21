"""Support information for feedback: versions, prefilled GitHub issue links, log helpers."""
import importlib.metadata
import platform
from urllib.parse import quote, urlencode

from .. import __version__
from ..adapters.logs import install_excepthook, log_dir, setup_logging, tail_log
from ..core import raw
from .develop import supported_labels

__all__ = ['app_version', 'system_info', 'issue_url', 'log_dir', 'setup_logging',
           'install_excepthook', 'tail_log', 'REPO_URL']

REPO_URL = 'https://github.com/sebastianriquelme1321/FilmSimulation'
TEMPLATES = {'feedback': ('feedback.yml', '[Feedback] '), 'bug': ('bug_report.yml', '[Bug] ')}
MAX_URL = 7000


def app_version() -> str:
    try:
        return importlib.metadata.version('film-poc')
    except importlib.metadata.PackageNotFoundError:
        return __version__


def _package(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return 'desconocida'


def system_info(theme: str = '', qt: str = '') -> str:
    """Multi-line environment summary; no paths or user names."""
    import rawpy
    supported_labels()  # registers the decoders
    lines = [
        f'FilmSimulation {app_version()}',
        f'Sistema: {platform.system()} {platform.release()} ({platform.machine()})',
        f'Python: {platform.python_version()}',
        f'PySide6: {_package("PySide6-Essentials")}' + (f' · Qt {qt}' if qt else ''),
        f'rawpy: {rawpy.__version__} · LibRaw {rawpy.libraw_version}',
        f'Formatos RAW: {", ".join(raw.supported_extensions())}',
    ]
    if theme:
        lines.append(f'Tema: {theme}')
    return '\n'.join(lines)


def issue_url(kind: str, extra: str = '', theme: str = '', qt: str = '') -> str:
    """New-issue link prefilled with system info (and a log tail); always < MAX_URL.

    GitHub issue forms are prefilled by field id (system, log, version, os); `body` is the
    fallback for plain templates."""
    template, prefix = TEMPLATES[kind]
    info = system_info(theme, qt)
    fields = {'template': template, 'title': prefix, 'body': f'```\n{info}\n```',
              'system': info, 'version': app_version(),
              'os': f'{platform.system()} {platform.release()} ({platform.machine()})'}

    def build(log):
        query = urlencode({**fields, **({'log': log} if log else {})}, quote_via=quote)
        return f'{REPO_URL}/issues/new?{query}'

    extra = extra.strip()
    url = build(extra)
    while len(url) > MAX_URL and extra:
        extra = extra[len(extra)//4:] if len(extra) > 400 else ''  # keep the newest lines
        url = build(extra)
    return url
