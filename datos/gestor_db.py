"""Gestor de base de datos SQLite para Horus Space Lab.

Administra el registro histórico estructurado de ensayos de motores cohete,
metadatos de muestras de propelente y series temporales de telemetría a alta velocidad.
"""

from __future__ import annotations

import csv
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class EnsayoMetadata:
    """Estructura de metadatos del ensayo y propiedades balísticas del motor."""

    codigo_ensayo: str
    operadores: str
    fecha: str = ""
    dias_vejez: int = 0
    diam_ext_mm: float = 0.0
    diam_int_mm: float = 0.0
    altura_mm: float = 0.0
    masa_propelente_g: float = 0.0
    temp_amb_c: float = 20.0
    humedad_pct: float = 50.0
    empuje_pico_n: float = 0.0
    empuje_prom_n: float = 0.0
    impulso_total_ns: float = 0.0
    isp_s: float = 0.0
    tiempo_quemado_s: float = 0.0
    velocidad_quemado_mm_s: float = 0.0
    clase_nakka: str = "N/A"
    notas: str = ""

    def __post_init__(self) -> None:
        if not self.fecha:
            self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class GestorBD:
    """Administrador centralizado de la base de datos relacional SQLite."""

    def __init__(self, ruta_db: Optional[str] = None) -> None:
        if ruta_db is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.ruta_db = os.path.join(base_dir, "horus_test_stand.db")
        else:
            self.ruta_db = ruta_db

        self._crear_tablas()

    def _obtener_conexion(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.ruta_db)
        con.row_factory = sqlite3.Row
        return con

    def _crear_tablas(self) -> None:
        """Inicializa los esquemas de metadatos y telemetría de ensayos."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ensayos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_ensayo TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    operadores TEXT,
                    dias_vejez INTEGER DEFAULT 0,
                    diam_ext_mm REAL DEFAULT 0.0,
                    diam_int_mm REAL DEFAULT 0.0,
                    altura_mm REAL DEFAULT 0.0,
                    masa_propelente_g REAL DEFAULT 0.0,
                    temp_amb_c REAL DEFAULT 20.0,
                    humedad_pct REAL DEFAULT 50.0,
                    empuje_pico_n REAL DEFAULT 0.0,
                    empuje_prom_n REAL DEFAULT 0.0,
                    impulso_total_ns REAL DEFAULT 0.0,
                    isp_s REAL DEFAULT 0.0,
                    tiempo_quemado_s REAL DEFAULT 0.0,
                    velocidad_quemado_mm_s REAL DEFAULT 0.0,
                    clase_nakka TEXT DEFAULT 'N/A',
                    notas TEXT
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetria_puntos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ensayo_id INTEGER NOT NULL,
                    tiempo_s REAL NOT NULL,
                    voltaje_v REAL NOT NULL,
                    empuje_n REAL NOT NULL,
                    impulso_ns REAL NOT NULL,
                    FOREIGN KEY (ensayo_id) REFERENCES ensayos (id) ON DELETE CASCADE
                );
                """
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetria_ensayo ON telemetria_puntos (ensayo_id);"
            )
            con.commit()

    def guardar_ensayo(
        self,
        meta: EnsayoMetadata,
        tiempos: list[float] | Any,
        voltajes: list[float] | Any,
        empujes: list[float] | Any,
        impulsos: list[float] | Any,
    ) -> int:
        """Almacena el registro balístico y la serie temporal completa por lote."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO ensayos (
                    codigo_ensayo, fecha, operadores, dias_vejez,
                    diam_ext_mm, diam_int_mm, altura_mm, masa_propelente_g,
                    temp_amb_c, humedad_pct, empuje_pico_n, empuje_prom_n,
                    impulso_total_ns, isp_s, tiempo_quemado_s,
                    velocidad_quemado_mm_s, clase_nakka, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    meta.codigo_ensayo,
                    meta.fecha,
                    meta.operadores,
                    meta.dias_vejez,
                    meta.diam_ext_mm,
                    meta.diam_int_mm,
                    meta.altura_mm,
                    meta.masa_propelente_g,
                    meta.temp_amb_c,
                    meta.humedad_pct,
                    meta.empuje_pico_n,
                    meta.empuje_prom_n,
                    meta.impulso_total_ns,
                    meta.isp_s,
                    meta.tiempo_quemado_s,
                    meta.velocidad_quemado_mm_s,
                    meta.clase_nakka,
                    meta.notas,
                ),
            )
            ensayo_id = cur.lastrowid

            # Inserción acelerada en bloque de la telemetría a 200 Hz
            n_puntos = min(len(tiempos), len(voltajes), len(empujes), len(impulsos))
            if n_puntos > 0:
                lote = [
                    (ensayo_id, float(tiempos[i]), float(voltajes[i]), float(empujes[i]), float(impulsos[i]))
                    for i in range(n_puntos)
                ]
                cur.executemany(
                    """
                    INSERT INTO telemetria_puntos (ensayo_id, tiempo_s, voltaje_v, empuje_n, impulso_ns)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    lote,
                )

            con.commit()
            return int(ensayo_id)

    def obtener_todos_ensayos(self) -> list[dict[str, Any]]:
        """Recupera la lista histórica de ensayos ordenados por fecha descendente."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM ensayos ORDER BY id DESC;")
            return [dict(fila) for fila in cur.fetchall()]

    def obtener_telemetria_ensayo(self, ensayo_id: int) -> dict[str, list[float]]:
        """Recupera las series temporales de un ensayo específico."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT tiempo_s, voltaje_v, empuje_n, impulso_ns
                FROM telemetria_puntos
                WHERE ensayo_id = ?
                ORDER BY tiempo_s ASC;
                """,
                (ensayo_id,),
            )
            filas = cur.fetchall()

        tiempos = [f["tiempo_s"] for f in filas]
        voltajes = [f["voltaje_v"] for f in filas]
        empujes = [f["empuje_n"] for f in filas]
        impulsos = [f["impulso_ns"] for f in filas]

        return {
            "tiempo": tiempos,
            "voltaje": voltajes,
            "empuje": empujes,
            "impulso": impulsos,
        }

    def eliminar_ensayo(self, ensayo_id: int) -> None:
        """Elimina un ensayo y toda su telemetría asociada."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM telemetria_puntos WHERE ensayo_id = ?;", (ensayo_id,))
            cur.execute("DELETE FROM ensayos WHERE id = ?;", (ensayo_id,))
            con.commit()

    def exportar_csv(self, ensayo_id: int, ruta_csv: str) -> None:
        """Exporta la corrida con metadatos en cabecera y telemetría completa."""
        with self._obtener_conexion() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM ensayos WHERE id = ?;", (ensayo_id,))
            ensayo_fila = cur.fetchone()

        if not ensayo_fila:
            raise ValueError(f"No existe el ensayo con ID {ensayo_id}")

        ensayo = dict(ensayo_fila)
        datos = self.obtener_telemetria_ensayo(ensayo_id)

        with open(ruta_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Cabecera de metadatos de instrumentación
            writer.writerow(["# HORUS SPACE LAB - REGISTRO DE TELEMETRÍA"])
            writer.writerow(["# Codigo Ensayo", ensayo["codigo_ensayo"]])
            writer.writerow(["# Fecha", ensayo["fecha"]])
            writer.writerow(["# Operadores", ensayo["operadores"]])
            writer.writerow(["# Dias de Vejez", ensayo["dias_vejez"]])
            writer.writerow(["# Masa Propelente (g)", ensayo["masa_propelente_g"]])
            writer.writerow(["# Empuje Pico (N)", ensayo["empuje_pico_n"]])
            writer.writerow(["# Empuje Promedio (N)", ensayo["empuje_prom_n"]])
            writer.writerow(["# Impulso Total (N*s)", ensayo["impulso_total_ns"]])
            writer.writerow(["# Isp (s)", ensayo["isp_s"]])
            writer.writerow(["# Tiempo Quemado (s)", ensayo["tiempo_quemado_s"]])
            writer.writerow(["# Velocidad Quemado (mm/s)", ensayo["velocidad_quemado_mm_s"]])
            writer.writerow(["# Clase Nakka/NAR", ensayo["clase_nakka"]])
            writer.writerow([])
            # Columnas de telemetría a 200 Hz
            writer.writerow(["tiempo_s", "voltaje_v", "empuje_n", "impulso_ns"])
            for i in range(len(datos["tiempo"])):
                writer.writerow([
                    f"{datos['tiempo'][i]:.4f}",
                    f"{datos['voltaje'][i]:.4f}",
                    f"{datos['empuje'][i]:.2f}",
                    f"{datos['impulso'][i]:.2f}",
                ])
