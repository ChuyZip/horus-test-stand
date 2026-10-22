# -*- mode: python ; coding: utf-8 -*-
import os
import sys

es_windows = sys.platform.startswith('win')
es_mac = sys.platform == 'darwin'

icono_app = 'HorusSlogan.ico' if (es_windows and os.path.exists('HorusSlogan.ico')) else None

datas = [
    ('estilo', 'estilo'),
    ('assets', 'assets'),
    ('logo.png', '.'),
    ('HorusSlogan.png', '.'),
]
if os.path.exists('HorusSlogan.ico'):
    datas.append(('HorusSlogan.ico', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PySide6.QtSvg', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HorusSpaceLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icono_app,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HorusSpaceLab',
)

if es_mac:
    app = BUNDLE(
        coll,
        name='HorusSpaceLab.app',
        icon=icono_app,
        bundle_identifier='com.horusspacelab.bancodepruebas',
    )
