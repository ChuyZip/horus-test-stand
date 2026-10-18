from PyQt6.QtWidgets import QApplication

from communication.protocols import ConnectionMode, PROTOCOL_CONFIGS
from ui.dialogs.voltage_characterization_window import VoltageCharacterizationWindow


def test_characterization_protocol_has_expected_layout() -> None:
    config = PROTOCOL_CONFIGS[ConnectionMode.CHARACTERIZATION]

    assert config.packet_size == 16
    assert config.struct_format == "<ffiI"
    assert config.is_characterization


def test_characterization_window_records_sample() -> None:
    app = QApplication.instance() or QApplication([])
    window = VoltageCharacterizationWindow()

    window.add_sample(0.6100, 1.3000, 123456, 7)

    assert window._weight_data == [0.6100]
    assert window._voltage_data == [1.3000]
    assert window._raw_data == [123456]
    assert window._sequence_data == [7]
    assert "secuencia 7" in window.status.text()
