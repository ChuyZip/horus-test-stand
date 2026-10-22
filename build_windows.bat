@echo off
title Compilador Horus Space Lab - Windows
echo ==========================================================
echo   HORUS SPACE LAB - Empaquetador para Windows (.exe)
echo ==========================================================
echo.

if not exist .venv (
    echo [1/3] Creando entorno virtual de Python...
    python -m venv .venv
)

echo [2/3] Activando entorno e instalando dependencias...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [3/3] Generando ejecutable con PyInstaller...
pyinstaller --noconfirm --clean HorusSpaceLab.spec

echo.
echo ==========================================================
echo   COMPILACION COMPLETADA!
echo   Tu aplicacion para Windows esta lista en:
echo   dist\HorusSpaceLab\HorusSpaceLab.exe
echo.
echo   NOTA: Para compartirla en otra PC con Windows, comprime
echo   toda la carpeta "dist\HorusSpaceLab" en un archivo .zip
echo ==========================================================
pause
