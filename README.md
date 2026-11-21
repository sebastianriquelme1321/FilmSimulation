# FilmSimulation

Aplicación de escritorio experimental para revelar RAW Sony y aplicar aproximaciones de película. Incluye 31 looks, filtros por origen, un visor con zoom y comparación antes/después, ajustes de exposición, color y grano, y exportación JPEG sRGB. Los nombres comerciales identifican el look buscado; no son perfiles oficiales.

![Tema Taller neutro](docs/images/workshop.png)

![Tema Vidrio y luz](docs/images/glass.png)

(Capturas generadas con una foto sintética; no incluyen fotografías reales.)

## Funciones

- Tres columnas: películas (looks) a la izquierda, visor en el centro y ajustes a la derecha.
- Importar un RAW con el botón **Importar RAW** o arrastrándolo sobre la ventana.
- Visor con zoom, desplazamiento y divisor antes/después arrastrable.
- Ajustes previos al look: exposición, temperatura, contraste, saturación y tinte; intensidad del look y grano.
- Biblioteca local de LUT `.cube`, HaldCLUT y recetas JSON.
- Exportación de JPEG procesado o de un ZIP con el RAW original y los ajustes.
- Dos temas: **Taller neutro** (predeterminado) y **Vidrio y luz**.
- Decodificación RAW basada en LibRaw para muchas marcas (Sony ARW verificado; el resto experimental) y decodificadores enchufables.

## Instalar y ejecutar

Requiere Python 3.12 o 3.13 de 64 bits. En Windows: `py -3.12 launch.py`. En macOS: `python3.12 launch.py`. El iniciador crea un entorno virtual e instala las dependencias. Después pueden usarse `Iniciar.cmd` o `bash Iniciar.command`.

macOS necesita versión 14 o posterior. Intel usa rawpy 0.25.1 y Apple Silicon 0.27.1; la compatibilidad en macOS debe confirmarse con pruebas reales. Este repositorio contiene fuentes, no un instalador firmado.

## Uso

1. Importa un RAW (botón **Importar RAW** o arrastrar y soltar un `.ARW` sobre la ventana).
2. Elige una película en la columna izquierda: clic en la tarjeta o Enter. Recorrer con las flechas no la aplica.
3. Ajusta exposición, temperatura, contraste, saturación, tinte, intensidad y grano en la columna derecha. **Restablecer ajustes** vuelve todo a neutro (mantiene película y grano).
4. Exporta con el selector y el botón **Exportar**.

**Visor.** Botones **Dividido**, **Antes** y **Después**; el selector **Fondo** cambia el color neutro alrededor de la foto (Gris, Negro, Blanco) y se recuerda al reabrir la aplicación.

| Acción | Gesto o tecla |
| --- | --- |
| Acercar / alejar | Rueda del ratón o gesto de desplazamiento del trackpad (alrededor del cursor); teclas `+` / `-` |
| Desplazar | Arrastrar con zoom aplicado |
| Mover el divisor | Arrastrar la línea blanca; flechas ←/→ (2 % por pulsación) en modo Dividido |
| Ajustar a la ventana | Tecla `0` o botón **Ajustar** |
| Tamaño 100 % | Tecla `1` o botón **100 %** |
| Alternar ajustar / 100 % | Doble clic sobre la foto |
| Exportar | `Cmd+E` (macOS) / `Ctrl+E` (Windows) o botón **Exportar** |

El visor necesita el foco (haz clic sobre él) para recibir las teclas. En el control de exposición, las flechas cambian 0,1 EV y RePág/AvPág 0,5 EV; también se puede escribir un valor exacto.

**Importante:** el visor trabaja sobre una vista previa de hasta 1280 px de lado largo, así que “100 %” se refiere a esa vista previa y no a los píxeles del RAW. La exportación sí usa la resolución completa.

## Biblioteca local

“Añadir LUT o receta” acepta LUT 3D `.cube` (2–65 puntos por eje), HaldCLUT PNG y recetas JSON versión 1. Las LUT deben esperar entrada sRGB; no se detectan ni convierten espacios Log. No se ejecuta código importado. “Guardar receta” guarda una combinación de look, ajustes, intensidad y grano; las recetas de ajustes JPEG de cámara no son directamente compatibles.

### Formato de receta (versión 1)

JSON con estas claves (cualquier otra se rechaza). Obligatorias: `version` (siempre `1`), `name` y `base_look` (nombre interno de un look instalado, p. ej. `Velvia/Vivid (aproximación)`, que no sea otra receta). Opcionales: `author`, `source`, `license` (texto, hasta 500 caracteres), `input_space` (solo `"sRGB"`), `strength` (intensidad, 0–1; por defecto 1), `grain` (uno de los valores del selector de grano; por defecto `"Desactivado"`), `exposure_ev` (−3 a 3), `temperature` (−100 a 100), y `contrast`, `saturation` y `tint` (−100 a 100, neutro en 0; si faltan se asume 0, de modo que las recetas antiguas siguen siendo válidas).

```json
{"version": 1, "name": "Mi receta", "base_look": "Velvia/Vivid (aproximación)", "strength": 0.8,
 "grain": "Desactivado", "exposure_ev": 0.3, "temperature": 10,
 "contrast": 15, "saturation": -10, "tint": 0}
```

La biblioteca se guarda fuera del repositorio: `%LOCALAPPDATA%/FilmPOC` en Windows y `~/Library/Application Support/FilmPOC` en macOS. La referencia de las tarjetas es una ilustración generada por código. Los archivos importados y las fotos del usuario no forman parte del proyecto.

## Desarrollo

```sh
python -m pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
python -m build
```

**Estructura.** El paquete `film_poc/` está en capas (`core`, `adapters`, `services`, `ui`) con una regla de dependencias comprobada por las pruebas. Ver [CONTRIBUTING.md](CONTRIBUTING.md).

Comprobaciones antes de enviar cambios: `ruff check .` (longitud de línea 100) y `QT_QPA_PLATFORM=offscreen python -m pytest -q`.

**Ejecutable.** Para generar `FilmSimulation.app` (macOS) o `FilmSimulation.exe` (Windows) con PyInstaller:

```sh
python -m pip install -e ".[dev]"
pyinstaller --noconfirm packaging/film-poc.spec   # resultado en dist/
```

Cada sistema (y, en macOS, cada arquitectura) debe compilarse en su propio equipo. Al subir una etiqueta `v*`, el workflow `release.yml` compila Windows, macOS arm64 y macOS Intel y adjunta los ZIP a un GitHub Release. Detalles en [packaging/README.md](packaging/README.md).

## Limitaciones conocidas

- El zoom del visor opera sobre una vista previa de hasta 1280 px; “100 %” no equivale a los píxeles del RAW.
- Solo Sony ARW se ha verificado con archivos reales. Las demás extensiones RAW (Canon, Nikon, Fujifilm, Panasonic, Olympus, Pentax, DNG, etc.) se decodifican con LibRaw y son **experimentales**, sin probar; si tu modelo no abre, reporta la cámara desde Ayuda > Enviar feedback. Si el RAW no trae previsualización incrustada, se revela sin igualar el tono de la cámara. Más detalle en [CONTRIBUTING.md](CONTRIBUTING.md).
- Las aplicaciones empaquetadas no están firmadas ni notarizadas por Apple ni Microsoft: macOS (Gatekeeper) y Windows (SmartScreen) mostrarán un aviso la primera vez; ver [packaging/README.md](packaging/README.md).
- La compatibilidad en macOS debe confirmarse con pruebas reales; las LUT esperan entrada sRGB.
- Las simulaciones son aproximaciones, sin equivalencia garantizada con cámaras o película reales.

El revelado usa rawpy/LibRaw y toma la miniatura de cámara como guía tonal cuando está disponible. Las simulaciones son aproximaciones y dependen del revelado y la escena. La exportación conserva resolución y añade un perfil ICC sRGB. No hay calibración colorimétrica ni equivalencia garantizada con cámaras Fujifilm o película analógica.

## Feedback y soporte

Es una beta gratuita y tu opinión importa. Usa **Ayuda > Enviar feedback…** o **Ayuda > Reportar un problema…**: se abre tu navegador con un formulario de GitHub ya rellenado con la versión y el sistema (sin rutas de archivos ni nombre de usuario) y, en el caso de un problema, el final del registro; revisa el texto y envíalo tú. **Ayuda > Copiar información del sistema** lo deja en el portapapeles.

El registro (`film_poc.log`, rotativo, sin rutas completas) se guarda en la carpeta `logs` de la biblioteca local; **Ayuda > Abrir carpeta de registros** la abre:

- macOS: `~/Library/Application Support/FilmPOC/logs`
- Windows: `%LOCALAPPDATA%\FilmPOC\logs`
- Linux: `~/.local/share/FilmPOC/logs`

Privacidad: no hay telemetría ni código de red. La aplicación no envía nada; los menús solo abren tu navegador o copian texto.

## Aviso

Proyecto independiente, sin afiliación ni respaldo de Kodak, Fujifilm, Ilford u otras marcas citadas. Los nombres de películas se usan solo para describir qué se aproxima. Los looks son aproximaciones y no equivalen a los procesos originales. Todo se procesa en tu equipo; la aplicación no envía datos.

## Licencias

Código combinado GPL-3.0-or-later; porciones adaptadas conservan sus atribuciones. LUT de película CC BY-SA 4.0 con avisos específicos. Consultar `LICENSE`, `THIRD_PARTY_NOTICES.md` y `film_poc/assets/film-stocks/ATTRIBUTION.md`. FujiLUT declara MIT en su README, sin aviso de copyright independiente en la revisión utilizada; esa declaración se conserva literalmente.

Las únicas imágenes incluidas son tablas técnicas LUT necesarias para el procesamiento. Este repositorio no incluye fotografías de prueba, resultados, investigación ni conversaciones.

## Ajustes y conservación del RAW

La exposición (−3 a +3 EV), la temperatura relativa y el tinte, el contraste y la saturación (−100 a 100, neutro en 0) se aplican en RGB lineal antes de codificar sRGB y aplicar el look. La temperatura es una corrección frío/cálido sobre el balance de cámara, no un ajuste de sensor calibrado en Kelvin; el tinte desplaza entre verde y magenta; el contraste actúa alrededor del gris medio. La intensidad mezcla la base ajustada y la simulación en sRGB; el grano se aplica después. La vista previa y la exportación usan el mismo proceso. Estos ajustes no recuperan información que el revelado inicial ya haya recortado.

El selector de exportación ofrece **JPEG procesado** o **RAW original + ajustes (.zip)**. El ZIP conserva el ARW byte por byte con sus metadatos originales, una receta JSON, un checksum SHA-256 y la LUT local cuando corresponde. No modifica el mosaico del sensor ni incorpora el look en el ARW. Para restaurar: extraer el archivo, importar el ARW y añadir `edit.recipe.json` a la biblioteca. Si incluye `library/`, copiar su contenido a la biblioteca local y reiniciar antes de importar la receta. Otros editores no interpretan automáticamente este formato. No se exporta DNG procesado.

Los perfiles incluidos y las LUT importadas trabajan con entrada sRGB. No hay conversión automática de Rec.709, S-Log u otras curvas Log; un selector de gamma por sí solo no corrige primarias, gamut ni la exposición de referencia de una LUT.

## Navegación y rendimiento

Buscar, cambiar de origen o recorrer tarjetas con las flechas no aplica una película. Haz clic en una tarjeta o confirma con Enter. La simulación activa se conserva aunque quede fuera del filtro; al importar una foto sin película seleccionada se muestra únicamente la base ajustada.

Las referencias se preparan en segundo plano. Las tablas decodificadas se guardan en una caché local descartable dentro de la biblioteca; la primera preparación puede tardar más. Si la caché falta o está dañada, se vuelve a calcular. Las vistas previas usan un máximo de 1280 píxeles de lado largo y un hilo independiente con una sola petición pendiente: al cambiar controles rápidamente se conserva el último ajuste. La base y la simulación se reutilizan al variar intensidad o grano. La exportación conserva la resolución original y el mismo proceso de color; no usa los píxeles reducidos de la previsualización.

## Apariencia

El selector **Tema**, en la esquina inferior derecha, alterna entre **Taller neutro** (predeterminado: grises neutros y un único acento azul) y **Vidrio y luz** (paneles translúcidos, acento ámbar y fondo ambiental derivado de la foto). La preferencia se conserva localmente. El visor de la fotografía usa un fondo neutro (Gris por defecto, o Negro/Blanco) en ambos temas. Cambiar de tema no reprocesa ni modifica la imagen exportada. El fondo ambiental se difumina a baja resolución y se reutiliza al mover los controles.
