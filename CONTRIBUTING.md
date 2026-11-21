# Contribuir

## Preparar el entorno

Requiere Python 3.12 (o 3.13).

```sh
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest -q            # las pruebas de UI no abren ventanas
ruff check .
python -m film_poc                                       # ejecutar la app
```

## Estructura

```
film_poc/
  core/      numpy puro: color, looks, grano, ajustes. Sin Qt, rawpy ni acceso a archivos
    looks/   un módulo por backend de look + registro (base.py)
  adapters/  mundo exterior: decodificador rawpy, LUT .cube/Hald, almacenamiento, assets
  services/  casos de uso: revelar, biblioteca, exportar JPEG/ZIP, preferencias
  ui/        solo Qt (PySide6): ventana, panel de ajustes, galería, tema
tests/       pytest; test_architecture.py vigila las capas
```

## Regla de dependencias

`ui -> services -> core` y `adapters -> core` (`services` también puede importar `adapters`).
Nunca al revés: `core` no importa nada de las otras capas, y `ui` no importa `rawpy` ni
`film_poc.adapters`.

`tests/test_architecture.py` recorre el AST de cada módulo (incluidos imports relativos y dentro
de funciones) y compara con la tabla `FORBIDDEN`. `core` tampoco puede importar `PySide6`, `rawpy`,
`PIL` ni `os`, `json`, `io`, `zipfile`, `sys`, etc. Además, no se admiten módulos sueltos en
`film_poc/` fuera de las cuatro capas. Si el test falla, mueve el código; no amplíes la tabla.

## Recetas

**a) Añadir un backend de look**
- `film_poc/core/looks/<nombre>.py`: clase con `apply(self, linear, look) -> float32` codificado
  para pantalla y, al final, `registry.add_backend('<nombre>', MiBackend())`. Los looks se
  añaden con `registry[nombre] = Look(...)` (ver `fuji.py`, `darktable.py`).
- `film_poc/core/looks/__init__.py`: añadir el módulo al `import` (el orden es el orden de `LOOKS`).
- Si necesita datos de disco, el core no lee archivos: cárgalos en un adaptador y regístralos con
  `core.tables.register_loader(kind, fn)`; el backend los pide con `tables.load(kind, clave)`
  (ejemplos: `looks/user_lut.py` y `adapters/lut_files.py`; el cableado está en
  `services/library.py::install`).
- Prueba en `tests/` (ver `tests/test_registry.py`).

**b) Añadir un formato RAW**
- `film_poc/adapters/<nombre>_decoder.py`: clase con `extensions` (minúsculas, con punto), `label`
  y `decode(path) -> (linear, reference)`, y `register_decoder(MiDecoder())` (de `core.raw`).
  Se importa solo: `adapters.load_decoders()` carga todo módulo `*_decoder`. Modelo:
  `adapters/rawpy_decoder.py`.
- El filtro del diálogo de apertura (`services/develop.py::open_filter`) y el texto de bienvenida
  se derivan de los decodificadores registrados. Pendiente a mano: los textos «Sony ARW» de
  `ui/window.py` y `services/export_bundle.py` aún asumen ARW.

**c) Añadir un control de UI**
- `film_poc/ui/adjustments_panel.py`: crear el widget, conectarlo a `self._changed` (emite
  `changed`) e incluirlo en `values()`, `reset()` y `set_values()`.
- `film_poc/ui/window.py`: ya escucha `adjustments.changed`; recoge el valor nuevo donde se usa
  `self.adjustments.values()`.
- Si cambia el resultado, la lógica va en `core/` (p. ej. `core/adjustments.py`) con su prueba;
  la UI solo transporta valores.

## Pruebas y CI

El workflow `.github/workflows/tests.yml` ejecuta `pytest -q` y `python -m build` en Windows y
macOS (arm64 e Intel) con `QT_QPA_PLATFORM=offscreen`. CI también ejecuta `ruff check .`:
pásalo antes de enviar.
Para el ejecutable, ver `packaging/README.md`.

## Checklist de PR

- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest -q` pasa, incluido `test_architecture.py`.
- [ ] `ruff check .` sin errores.
- [ ] Cambio en la capa correcta; sin imports que rompan la regla.
- [ ] Prueba nueva o actualizada para el comportamiento cambiado.
- [ ] Si añades datos de terceros, actualiza `THIRD_PARTY_NOTICES.md` y su atribución.
