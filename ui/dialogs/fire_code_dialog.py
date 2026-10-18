"""Confirmacion de codigo para la accion de ignicion."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class FireCodeDialog(QDialog):
    """Solicita el codigo temporal mostrado antes de permitir la ignicion."""

    def __init__(self, code: str, parent=None) -> None:
        super().__init__(parent)
        self._code = code
        self.setWindowTitle("Confirmar ignicion")
        self.setModal(True)
        self.setFixedWidth(390)
        self.setStyleSheet(
            "QDialog{background:#1a120b;}"
            "QLabel{color:#dddddd;font-family:'Courier New',monospace;}"
            "QLineEdit{background:#1a120b;color:#ffffff;border:1px solid #c4342d;"
            "padding:10px;font-size:20px;font-family:'Courier New',monospace;}"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("CONFIRMACION DE IGNICION")
        title.setStyleSheet("color:#c4342d;font-size:15px;font-weight:bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        instruction = QLabel("Ingresa este codigo de cuatro digitos para activar FIRE")
        instruction.setWordWrap(True)
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction)

        code_label = QLabel(self._code)
        code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_label.setStyleSheet(
            "color:#ffffff;background:#2e1614;border:1px solid #c4342d;"
            "padding:12px;font-family:'Courier New',monospace;font-size:30px;font-weight:bold;"
        )
        layout.addWidget(code_label)

        self.input_code = QLineEdit()
        self.input_code.setInputMask("0000;_")
        self.input_code.setPlaceholderText("0000")
        self.input_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_code.returnPressed.connect(self._confirm)
        layout.addWidget(self.input_code)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color:#d4567a;")
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        cancel = QPushButton("CANCELAR")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("CONFIRMAR FIRE")
        confirm.setStyleSheet(
            "background:#4a1510;color:#ffdddd;border:1px solid #c4342d;"
            "padding:8px 16px;font-weight:bold;"
        )
        confirm.clicked.connect(self._confirm)
        actions.addWidget(cancel)
        actions.addWidget(confirm)
        layout.addLayout(actions)

    def _confirm(self) -> None:
        if self.input_code.text() == self._code:
            self.accept()
        else:
            self.error_label.setText("Codigo incorrecto. Sistema desarmado.")
            self.input_code.clear()
            self.input_code.setFocus()

