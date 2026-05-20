@echo off
:: Este archivo funciona como un boton directo. Ejecuta la aplicacion sin mostrar una ventana de consola molesta.
cd /d "%~dp0"
start "" "venv\Scripts\pythonw.exe" "main.py"
