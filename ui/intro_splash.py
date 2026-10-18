"""Pantalla de inicio de Horus Space Lab."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from utils.paths import resource_path


class IntroSplash(QWidget):
    """Muestra el logo de Horus antes de abrir el dashboard."""

    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(920, 520)
        self.setStyleSheet("background:#1a120b;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(18)

        layout.addStretch(1)
        self.logo = QLabel()
        pixmap = QPixmap(resource_path("HSL_transparent.png"))
        self.logo.setPixmap(
            pixmap.scaled(
                760,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo)

        accent = QFrame()
        accent.setFixedHeight(2)
        accent.setStyleSheet("background:#40c4aa;border:0;")
        layout.addWidget(accent)
        layout.addStretch(1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        screen = self.screen()
        if screen:
            self.move(screen.availableGeometry().center() - self.rect().center())
        QTimer.singleShot(2500, self._finish)

    def _finish(self) -> None:
        self.finished.emit()
        self.close()
