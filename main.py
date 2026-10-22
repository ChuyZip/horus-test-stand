"""Punto de entrada principal para la estación de telemetría Horus Space Lab.

Configuración de entorno para macOS (Apple Silicon / Intel):
- Detección y asignación automática de QT_PLUGIN_PATH y QT_QPA_PLATFORM_PLUGIN_PATH
  apuntando a los plugins de PySide6 para garantizar la carga del plugin 'cocoa'.
- Forzado de PySide6 como backend de pyqtgraph.
- Aplicación de hoja de estilos QSS centralizada y configuración de icono de aplicación.
"""

from __future__ import annotations

import logging
import os
import platform
import sys

# ==============================================================================
# CONFIGURACIÓN AUTOMÁTICA DE PLUGINS QT PARA MACOS (COCOA)
# ==============================================================================
def configurar_entorno_qt_macos() -> None:
    """Configura las variables de entorno de plugins para evitar errores de Qt Cocoa en macOS."""
    os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

    # Cuando está empaquetado con PyInstaller (frozen), PyInstaller ya configura
    # las rutas internas de Qt automáticamente para cada sistema operativo.
    if getattr(sys, "frozen", False) or platform.system() != "Darwin":
        return

    try:
        import PySide6
        from PySide6.QtCore import QLibraryInfo

        ruta_plugins = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
        if not os.path.exists(ruta_plugins):
            # Ruta alternativa dentro del paquete PySide6 en entornos virtuales
            pyside_dir = os.path.dirname(PySide6.__file__)
            candidatos = [
                os.path.join(pyside_dir, "Qt", "plugins"),
                os.path.join(pyside_dir, "plugins"),
            ]
            for cand in candidatos:
                if os.path.exists(cand):
                    ruta_plugins = cand
                    break

        if os.path.exists(ruta_plugins):
            os.environ["QT_PLUGIN_PATH"] = ruta_plugins
            ruta_platforms = os.path.join(ruta_plugins, "platforms")
            if os.path.exists(ruta_platforms):
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ruta_platforms
                logging.info(f"Plugins de Qt Cocoa configurados en: {ruta_platforms}")

    except Exception as e:
        logging.warning(f"No fue posible auto-configurar rutas de plugins de Qt: {e}")


# Ejecutar la corrección antes de inicializar cualquier componente gráfico
configurar_entorno_qt_macos()

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from estilo.tema import obtener_hoja_estilos_qss
from ui.main_window import MainWindow


def main() -> None:
    """Inicializa y arranca la aplicación de instrumentación científica."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # En Windows, registrar AppUserModelID para que la barra de tareas muestre el icono propio
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "HorusSpaceLab.BancoDePruebas.2026"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("HorusBancoDePruebas")
    app.setApplicationDisplayName("Horus Space Lab - Banco de Pruebas")
    app.setOrganizationName("Horus Space Lab")

    # Aplicar icono global de la aplicación
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    rutas_icono = [
        os.path.join(base_dir, "assets", "logo.png"),
        os.path.join(base_dir, "logo.png"),
        os.path.join(base_dir, "HorusSlogan.png"),
        os.path.join(base_dir, "HorusSlogan.ico"),
    ]
    for ruta in rutas_icono:
        if os.path.exists(ruta):
            app.setWindowIcon(QIcon(ruta))
            break

    # Cargar y aplicar hoja de estilos QSS centralizada
    app.setStyleSheet(obtener_hoja_estilos_qss())

    # Instanciar y presentar ventana principal
    ventana = MainWindow()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
