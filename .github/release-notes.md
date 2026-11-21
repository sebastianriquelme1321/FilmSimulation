## FilmSimulation (beta)

App de escritorio **gratuita y de código abierto** (GPL-3.0) para revelar fotos RAW y aplicar simulaciones
de película. Todo corre en tu equipo: sin cuentas, sin nube y sin telemetría.
*Free, open-source desktop app to develop RAW photos and apply film simulations. Everything runs locally.*

### Descargas / Downloads
| Sistema | Archivo |
| --- | --- |
| macOS, Apple Silicon (M1 o posterior) | `FilmSimulation-macos-arm64.zip` |
| macOS, Intel | `FilmSimulation-macos-x86_64.zip` |
| Windows 64-bit | `FilmSimulation-windows-x64.zip` |

### Cómo abrirla (la app no está firmada) / How to open (the app is not signed)
- **macOS**: descomprime, arrastra `FilmSimulation.app` a *Aplicaciones* y la primera vez haz
  **clic derecho → Abrir → Abrir**. Si aun así macOS la bloquea:
  `xattr -dr com.apple.quarantine /Applications/FilmSimulation.app`
- **Windows**: descomprime la carpeta y ejecuta `FilmSimulation.exe`. Si aparece SmartScreen:
  **Más información → Ejecutar de todas formas**.

### Estado de esta beta / Beta status
- Verificado con fotos reales: **Sony ARW** en macOS.
- Otros formatos RAW (Canon, Nikon, Fuji, Panasonic, Olympus, Pentax, DNG…): **experimentales, sin probar**.
- **Windows**: compila y pasa los tests automáticos, pero aún no se ha probado manualmente.
- Los looks son **aproximaciones**; no equivalen a los procesos originales de cada película.

### Feedback
Menú **Ayuda → Enviar feedback** dentro de la app, o abre un
[issue](https://github.com/sebastianriquelme1321/FilmSimulation/issues/new/choose) /
[discusión](https://github.com/sebastianriquelme1321/FilmSimulation/discussions).
Si un archivo no abre, indica **la marca y el modelo de tu cámara** y el formato (CR3, NEF, RAF…).

Proyecto independiente, sin afiliación con Kodak, Fujifilm, Ilford ni otras marcas citadas.

---
