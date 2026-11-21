"""Dependency rule: ui -> services -> core, adapters -> core, services -> adapters.

Checked on the AST of every module (imports inside functions included), so it needs no Qt.
"""
import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / 'film_poc'
LAYERS = ('core', 'adapters', 'services', 'ui')

# layer -> top-level modules/packages it must not import
FORBIDDEN = {
    'core': {'PySide6', 'rawpy', 'PIL', 'film_poc.adapters', 'film_poc.services', 'film_poc.ui',
             'os', 'shutil', 'tempfile', 'json', 'io', 'zipfile', 'sys'},
    'adapters': {'PySide6', 'film_poc.services', 'film_poc.ui'},
    'services': {'PySide6', 'film_poc.ui'},
    'ui': {'rawpy', 'film_poc.adapters'},
}


def imported_modules(path: Path) -> set[str]:
    """Absolute dotted names imported by the file (relative imports resolved)."""
    package = ['film_poc', *path.relative_to(PACKAGE).parts[:-1]]  # the module's package
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - node.level + 1]
                module = '.'.join([*base, *([node.module] if node.module else [])])
                found.add(module)
                found.update(f'{module}.{alias.name}' for alias in node.names)
            else:
                found.add(node.module)
                found.update(f'{node.module}.{alias.name}' for alias in node.names)
    return found


def violates(module: str, forbidden: set[str]) -> bool:
    return any(module == name or module.startswith(name + '.') for name in forbidden)


@pytest.mark.parametrize('layer', LAYERS)
def test_layer_imports_only_allowed_modules(layer):
    problems = []
    for path in sorted((PACKAGE / layer).rglob('*.py')):
        for module in imported_modules(path):
            if violates(module, FORBIDDEN[layer]):
                problems.append(f'{path.relative_to(PACKAGE)} imports {module}')
    assert not problems, '\n'.join(problems)


def test_every_module_belongs_to_a_layer():
    stray = [p.name for p in PACKAGE.glob('*.py') if p.name not in ('__init__.py', '__main__.py')]
    assert not stray, f'Modules outside core/adapters/services/ui: {stray}'


def test_checker_detects_a_violation(tmp_path):
    """Guard the guard: the AST walk must see relative and in-function imports."""
    sample = PACKAGE / 'core' / '_probe.py'
    sample.write_text('def f():\n    from ..adapters import storage\n    import PySide6\n')
    try:
        found = imported_modules(sample)
    finally:
        sample.unlink()
    assert 'film_poc.adapters.storage' in found and 'PySide6' in found
