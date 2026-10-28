"""Portable first-run setup; run using Python 3.12 (Windows or macOS)."""
from pathlib import Path
import subprocess
import sys
import venv


def main():
    if not (3,12) <= sys.version_info[:2] < (3,14):
        raise SystemExit('Usa Python 3.12 o 3.13 de 64 bits.')
    root=Path(__file__).resolve().parent
    environment=root/'.venv'
    python=environment/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(python),'-m','pip','install','-e',str(root)],check=True)
    subprocess.run([str(python),'-m','film_poc'],cwd=root,check=True)


if __name__=='__main__':
    main()
