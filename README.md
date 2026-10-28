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

## Ajustes y conservación del RAW

La exposición (−3 a +3 EV) y la temperatura relativa se aplican en RGB lineal antes de codificar sRGB y aplicar el look. La temperatura es una corrección frío/cálido sobre el balance de cámara, no un ajuste de sensor calibrado en Kelvin. La intensidad mezcla la base ajustada y la simulación en sRGB; el grano se aplica después. La vista previa y la exportación usan el mismo proceso. Estos ajustes no recuperan información que el revelado inicial ya haya recortado.

El selector de exportación ofrece **JPEG procesado** o **RAW original + ajustes (.zip)**. El ZIP conserva el ARW byte por byte con sus metadatos originales, una receta JSON, un checksum SHA-256 y la LUT local cuando corresponde. No modifica el mosaico del sensor ni incorpora el look en el ARW. Para restaurar: extraer el archivo, importar el ARW y añadir `edit.recipe.json` a la biblioteca. Si incluye `library/`, copiar su contenido a la biblioteca local y reiniciar antes de importar la receta. Otros editores no interpretan automáticamente este formato. No se exporta DNG procesado.

Los perfiles incluidos y las LUT importadas trabajan con entrada sRGB. No hay conversión automática de Rec.709, S-Log u otras curvas Log; un selector de gamma por sí solo no corrige primarias, gamut ni la exposición de referencia de una LUT.

## Navegación y rendimiento

Buscar, cambiar de origen o recorrer tarjetas con las flechas no aplica una película. Haz clic en una tarjeta o confirma con Enter. La simulación activa se conserva aunque quede fuera del filtro; al importar una foto sin película seleccionada se muestra únicamente la base ajustada.

Las referencias se preparan en segundo plano. Las tablas decodificadas se guardan en una caché local descartable dentro de la biblioteca; la primera preparación puede tardar más. Si la caché falta o está dañada, se vuelve a calcular. Las vistas previas usan un máximo de 1280 píxeles de lado largo y un hilo independiente con una sola petición pendiente: al cambiar controles rápidamente se conserva el último ajuste. La base y la simulación se reutilizan al variar intensidad o grano. La exportación conserva la resolución original y el mismo proceso de color; no usa los píxeles reducidos de la previsualización.
