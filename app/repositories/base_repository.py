"""Responsabilidad única: persistencia en tbl_sensors_data_temp.

El SQL es común a SQLite y SQL Server; cada motor solo cambia la conexión,
cómo limitar filas y la optimización de inserción masiva.
"""
from abc import ABC, abstractmethod
from datetime import datetime, time, timedelta

import pandas as pd

from app.domain.models import MeasurementFilter

_ALLOWED_DISTINCT = {"block_name", "data_type"}
_BATCH = 20_000


class BaseRepository(ABC):
    def __init__(self, table_name: str):
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Nombre de tabla inválido")
        self.table = table_name

    @abstractmethod
    def connect(self): ...

    @abstractmethod
    def _limit_sql(self, select_sql: str, limit: int) -> str: ...

    def _prepare_cursor(self, cursor):
        """Gancho para optimizar la inserción masiva."""

    # ------------------------------------------------------------- escritura
    def replace_period(self, records: pd.DataFrame, create_ip=None) -> int:
        """Inserta los registros. Si el mismo periodo ya se había cargado, lo reemplaza
        (así subir dos veces el mismo Excel no duplica datos). Todo en una transacción."""
        now = datetime.now().replace(microsecond=0)
        rows = [
            (int(r.id_sensor), r.data_type, float(r.data_value), r.data_date.to_pydatetime()
             if hasattr(r.data_date, "to_pydatetime") else r.data_date, r.block_name, now, create_ip)
            for r in records.itertuples(index=False)
        ]
        start, end = records["data_date"].min(), records["data_date"].max()
        types = sorted(records["data_type"].unique())
        marks = ", ".join("?" for _ in types)

        with self.connect() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"DELETE FROM {self.table} WHERE data_date BETWEEN ? AND ? AND data_type IN ({marks})",
                    [self._dt(start), self._dt(end), *types])
                self._prepare_cursor(cur)
                sql = (f"INSERT INTO {self.table} (id_sensor, data_type, data_value, data_date, block_name, "
                       f"create_date, create_ip) VALUES (?, ?, ?, ?, ?, ?, ?)")
                for i in range(0, len(rows), _BATCH):
                    cur.executemany(sql, rows[i:i + _BATCH])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return len(rows)

    # --------------------------------------------------------------- lectura
    def find(self, f: MeasurementFilter, limit: int = 500):
        where, params = self._where(f)
        sql = (f"SELECT data_date, block_name, data_type, data_value, id_sensor FROM {self.table}"
               f"{where} ORDER BY data_date DESC, block_name, data_type")
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(self._limit_sql(sql, limit), params)
            return [self._row(r) for r in cur.fetchall()]

    def count(self, f: MeasurementFilter) -> int:
        where, params = self._where(f)
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self.table}{where}", params)
            return cur.fetchone()[0]

    def distinct(self, column: str):
        if column not in _ALLOWED_DISTINCT:
            raise ValueError(column)
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT {column} FROM {self.table} ORDER BY {column}")
            return [str(r[0]).strip() for r in cur.fetchall()]

    # -------------------------------------------------------------- helpers
    def _where(self, f: MeasurementFilter):
        clauses, params = [], []
        if f.fecha_inicio:
            clauses.append("data_date >= ?")
            params.append(self._dt(datetime.combine(f.fecha_inicio, time.min)))
        if f.fecha_fin:  # fecha_fin inclusiva: hasta el final de ese día
            clauses.append("data_date < ?")
            params.append(self._dt(datetime.combine(f.fecha_fin, time.min) + timedelta(days=1)))
        if f.block_name:
            clauses.append("block_name = ?")
            params.append(f.block_name)
        if f.data_type:
            clauses.append("data_type = ?")
            params.append(f.data_type)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), params

    @staticmethod
    def _dt(value):
        return value.to_pydatetime() if hasattr(value, "to_pydatetime") else value

    @staticmethod
    def _row(r):
        d = r[0]
        return {
            "data_date": d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)[:16],
            "block_name": str(r[1]).strip(),
            "data_type": str(r[2]).strip(),
            "data_value": round(float(r[3]), 2),
            "id_sensor": r[4],
        }
