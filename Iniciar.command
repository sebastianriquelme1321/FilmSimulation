#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python -m film_poc
fi
printf 'Primero ejecuta: python3.12 launch.py\n'
read -r -p 'Pulsa Enter para cerrar…'
