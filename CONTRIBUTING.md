# Contribuir

## Preparar el entorno

Requiere Python 3.12 (o 3.13).

```sh
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest -q            # las pruebas de UI no abren ventanas
ruff check .                                             # longitud de línea 100
python -m film_poc                                       # ejecutar la app
```

## Estructura

```
film_poc/
  core/      numpy puro: color, looks, grano, ajustes. Sin Qt, rawpy ni acceso a archivos
    looks/   un módulo por backend de look + registro (base.py)
  adapters/  mundo exterior: decodificador rawpy, LUT .cube/Hald, almacenamiento, assets
  services/  casos de uso: revelar, biblioteca, exportar JPEG/ZIP, preferencias
  ui/        solo Qt (PySide6): ventana, visor (viewer.py), panel de ajustes, galería, tema
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
  `adapters/rawpy_decoder.py`. `decode` puede devolver `reference=None` si no hay previsualización
  (se omite el ajuste de tono) y debe lanzar `ValueError` con mensaje en español si falla.
- Hoy un único decodificador LibRaw (`rawpy_decoder.py`) cubre `.arw .srf .sr2 .cr2 .cr3 .crw .nef
  .nrw .raf .rw2 .orf .pef .dng .srw .3fr .iiq .erf .mrw .kdc .dcr .raw`. Solo Sony ARW está
  verificado con archivos reales; el resto es EXPERIMENTAL y sin probar. Los modelos no
  compatibles se pueden reportar (Ayuda > Enviar feedback).
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

**d) Añadir o ajustar un tema (paleta)**
- `film_poc/ui/theme.py`: añadir la clave y su etiqueta a `THEMES` y un diccionario de tokens a
  `PALETTES` (parte de `_COMMON` y define todos los tokens que usa `_CSS`: `window`, `panel`,
  `field`, `edge`, `ink`, `accent`, etc.). La hoja de estilos se genera con `stylesheet(tema)`.
- `ui/window.py::apply_theme` y `ui/backdrop.py` tienen ramas específicas para `'glass'`
  (márgenes, marca, fondo ambiental); un tema nuevo con aspecto distinto puede necesitar ahí su rama.
- El visor de la foto usa fondos neutros propios (`SURROUNDS` en `ui/viewer.py`), independientes
  del tema. `tests/test_theme_contrast.py` comprueba el contraste de cada paleta: ejecútalo.

## Capturas de pantalla sin ventana

Con `QT_QPA_PLATFORM=offscreen` se puede dibujar la ventana real y guardarla (ejemplo, desde la
raíz del repositorio; usa un array sintético, no una foto real):

```python
import time
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import QApplication
from film_poc.ui.window import Window

app = QApplication([])
w = Window(); w.resize(1500, 900); w.show()
w.loaded(Path('foto.ARW'), np.random.rand(800, 1200, 3).astype('float32'))  # RGB lineal
def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(); time.sleep(.01)
while not w.pixmaps or w.preview_job is not None:   # espera a la vista previa
    pump(.1)
w.gallery.look.setCurrentIndex(3); pump(1.5)        # elige un look y espera el render
w.grab().save('captura.png')
```

Ejecútalo con `PYTHONPATH=. QT_QPA_PLATFORM=offscreen python script.py`. Ojo: cambiar el selector
de tema (`theme_selector`) guarda la preferencia en la biblioteca local; usa `w.apply_theme('glass')`
para no tocarla. Las capturas de `docs/images/` se generaron así.

## Pruebas y CI

El workflow `.github/workflows/tests.yml` ejecuta `pytest -q` y `python -m build` en Windows y
macOS (arm64 e Intel) con `QT_QPA_PLATFORM=offscreen`, tras `ruff check .` (longitud de línea 100,
reglas E, F, I, B): pásalo antes de enviar. El workflow `release.yml` compila el ejecutable
(PyInstaller, `packaging/film-poc.spec`) al subir una etiqueta `v*`; ver `packaging/README.md`.

## Checklist de PR

- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest -q` pasa, incluido `test_architecture.py`.
- [ ] `ruff check .` sin errores.
- [ ] Cambio en la capa correcta; sin imports que rompan la regla.
- [ ] Prueba nueva o actualizada para el comportamiento cambiado.
- [ ] Si añades datos de terceros, actualiza `THIRD_PARTY_NOTICES.md` y su atribución.
