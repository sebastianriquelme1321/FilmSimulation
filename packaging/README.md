# Empaquetado (PyInstaller)

## Compilar en local
```
python -m pip install -e ".[dev]" pyinstaller
pyinstaller --noconfirm packaging/film-poc.spec
```
Resultado en `dist/`: `FilmSimulation.app` (macOS) o `dist/FilmSimulation/FilmSimulation.exe` (Windows).
Cada sistema debe compilarse en su propio sistema operativo (y arquitectura en macOS).

## Compartir
- macOS: `ditto -c -k --keepParent dist/FilmSimulation.app FilmSimulation-mac.zip`
- Windows: comprimir la carpeta `dist/FilmSimulation` en un .zip.
- Automatico: al subir una tag `v*` (p. ej. `git tag v0.7.0-beta.1 && git push --tags`) el workflow
  `release.yml` compila Windows, macOS arm64 y macOS Intel y los adjunta a un GitHub Release.

## Apps sin firmar
- macOS (Gatekeeper): clic derecho sobre la app > Abrir > Abrir. Si aun asi bloquea:
  `xattr -dr com.apple.quarantine FilmSimulation.app`. Evitarlo requiere firmar y notarizar,
  lo que necesita una cuenta de pago de Apple Developer (no esta configurado).
- Windows (SmartScreen): "Mas informacion" > "Ejecutar de todas formas".
