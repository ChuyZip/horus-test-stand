#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  HORUS SPACE LAB - Empaquetador para Linux (x86_64)"
echo "=========================================================="
echo ""

if [ ! -d ".venv" ]; then
    echo "[1/3] Creando entorno virtual de Python..."
    python3 -m venv .venv
fi

echo "[2/3] Activando entorno e instalando dependencias..."
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo "[3/3] Generando ejecutable con PyInstaller..."
pyinstaller --noconfirm --clean HorusSpaceLab.spec

echo ""
echo "=========================================================="
echo "  ¡COMPILACIÓN COMPLETADA!"
echo "  Tu aplicación para Linux está lista en:"
echo "  dist/HorusSpaceLab/HorusSpaceLab"
echo "=========================================================="
