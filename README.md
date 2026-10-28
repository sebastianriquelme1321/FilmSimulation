# FilmSimulation

Aplicación de escritorio experimental para revelar RAW Sony y aplicar aproximaciones de película. Incluye 31 looks, filtros por origen, comparación antes/después, grano y exportación JPEG sRGB. Los nombres comerciales identifican el look buscado; no son perfiles oficiales.

## Instalar y ejecutar

Requiere Python 3.12 o 3.13 de 64 bits. En Windows: `py -3.12 launch.py`. En macOS: `python3.12 launch.py`. El iniciador crea un entorno virtual e instala las dependencias. Después pueden usarse `Iniciar.cmd` o `bash Iniciar.command`.

macOS necesita versión 14 o posterior. Intel usa rawpy 0.25.1 y Apple Silicon 0.27.1; la compatibilidad en macOS debe confirmarse con pruebas reales. Este repositorio contiene fuentes, no un instalador firmado.

## Biblioteca local

“Añadir LUT o receta” acepta LUT 3D `.cube` (2–65 puntos por eje), HaldCLUT PNG y recetas JSON versión 1. Las LUT deben esperar entrada sRGB; no se detectan ni convierten espacios Log. No se ejecuta código importado. “Guardar receta” guarda una combinación de look, intensidad y grano; las recetas de ajustes JPEG de cámara no son directamente compatibles.

La biblioteca se guarda fuera del repositorio: `%LOCALAPPDATA%/FilmPOC` en Windows y `~/Library/Application Support/FilmPOC` en macOS. La referencia de las tarjetas es una ilustración generada por código. Los archivos importados y las fotos del usuario no forman parte del proyecto.

## Desarrollo

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m build
```

El revelado usa rawpy/LibRaw y toma la miniatura de cámara como guía tonal cuando está disponible. Las simulaciones son aproximaciones y dependen del revelado y la escena. La exportación conserva resolución y añade un perfil ICC sRGB. No hay calibración colorimétrica ni equivalencia garantizada con cámaras Fujifilm o película analógica.

## Licencias

Código combinado GPL-3.0-or-later; porciones adaptadas conservan sus atribuciones. LUT de película CC BY-SA 4.0 con avisos específicos. Consultar `LICENSE`, `THIRD_PARTY_NOTICES.md` y `film_poc/assets/film-stocks/ATTRIBUTION.md`. FujiLUT declara MIT en su README, sin aviso de copyright independiente en la revisión utilizada; esa declaración se conserva literalmente.

Las únicas imágenes incluidas son tablas técnicas LUT necesarias para el procesamiento. Este repositorio no incluye fotografías de prueba, resultados, investigación ni conversaciones.
