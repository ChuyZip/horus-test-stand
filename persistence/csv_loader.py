"""Carga de archivos CSV de telemetria para su analisis posterior."""
from __future__ import annotations

import csv
from dataclasses import dataclass

from config.constants import GRAVITY


@dataclass(frozen=True)
class CsvTelemetryData:
    """Series de telemetria recuperadas desde un archivo CSV."""

    time_data: list[float]
    thrust_n: list[float]
    impulse_ns: list[float]


def load_telemetry_csv(filepath: str) -> CsvTelemetryData:
    """Carga tiempo, empuje e impulso desde un CSV exportado por Horus.

    Acepta los CSV de exportacion manual y los de autoguardado. Cuando el
    archivo no contiene la columna de impulso, esta se integra desde empuje.
    """
    with open(filepath, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise ValueError("El archivo CSV no contiene encabezados.")

        columns = {_normalize_header(name): name for name in reader.fieldnames}
        time_column = columns.get("tiempo (s)")
        thrust_column = columns.get("empuje (n)")
        impulse_column = columns.get("impulso acum (ns)")

        if time_column is None or thrust_column is None:
            raise ValueError(
                "El CSV debe incluir las columnas 'Tiempo (s)' y 'Empuje (N)'."
            )

        time_data: list[float] = []
        thrust_n: list[float] = []
        impulse_values: list[float | None] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                time_data.append(float(row[time_column]))
                thrust_n.append(float(row[thrust_column]))
                impulse_values.append(
                    float(row[impulse_column]) if impulse_column and row[impulse_column] else None
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"Dato invalido en la fila {line_number}.") from error

    if not time_data:
        raise ValueError("El archivo CSV no contiene mediciones.")

    if all(value is not None for value in impulse_values):
        impulse_ns = [value for value in impulse_values if value is not None]
    else:
        impulse_ns = _calculate_impulse(time_data, thrust_n)

    return CsvTelemetryData(time_data=time_data, thrust_n=thrust_n, impulse_ns=impulse_ns)


def _normalize_header(header: str | None) -> str:
    return (header or "").strip().lower()


def _calculate_impulse(time_data: list[float], thrust_n: list[float]) -> list[float]:
    impulse_ns = [0.0]
    for index in range(1, len(time_data)):
        dt = max(0.0, time_data[index] - time_data[index - 1])
        impulse_ns.append(impulse_ns[-1] + thrust_n[index] * dt)
    return impulse_ns
