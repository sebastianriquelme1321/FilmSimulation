@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m film_poc
) else (
  py -3.12 launch.py
)
if errorlevel 1 pause
