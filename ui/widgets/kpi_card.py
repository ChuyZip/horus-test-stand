"""
Widget de tarjeta de KPI para la interfaz de telemetría.
"""
from typing import Union
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel

class KpiCard(QFrame):
    """
    Tarjeta de indicador clave de rendimiento (KPI) que muestra un título, valor y unidad.
    """
    def __init__(
        self,
        label: str,
        unit: str,
        color: str = "#40c4aa",
        tooltip: str = "",
        parent=None,
    ) -> None:
        """
        Inicializa la tarjeta KPI.
        
        Args:
            label: Etiqueta o título del KPI.
            unit: Unidad de medida.
            color: Color del texto y bordes.
            parent: Widget padre.
        """
        super().__init__(parent)
        self.color = color
        if tooltip:
            self.setToolTip(tooltip)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"KpiCard{{background:#261c13;border:1px solid {color}44;border-radius:8px;}}")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        
        self.lbl_title = QLabel(label.upper())
        self.lbl_title.setStyleSheet(f"color:{color};font-size:10px;letter-spacing:2px;")
        
        self.lbl_value = QLabel("—")
        self.lbl_value.setStyleSheet("color:#ffffff;font-size:24px;font-weight:bold;")
        
        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet(f"color:{color}88;font-size:11px;")
        
        if tooltip:
            self.lbl_title.setToolTip(tooltip)
            self.lbl_value.setToolTip(tooltip)
            self.lbl_unit.setToolTip(tooltip)

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)
        lay.addWidget(self.lbl_unit)

    def set_value(self, val: Union[float, int, str], decimals: int = 2) -> None:
        """
        Establece el valor a mostrar.
        
        Args:
            val: Valor numérico o texto a mostrar.
            decimals: Cantidad de decimales si el valor es numérico.
        """
        if isinstance(val, (float, int)):
            self.lbl_value.setText(f"{val:.{decimals}f}")
        else:
            self.lbl_value.setText(str(val))

    def reset(self) -> None:
        """Restablece el valor mostrado al estado por defecto."""
        self.lbl_value.setText("—")
