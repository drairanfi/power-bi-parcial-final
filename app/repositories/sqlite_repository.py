"""Repositorio SQLite: sirve para probar sin tener SQL Server instalado."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.repositories.base_repository import BaseRepository

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "create_table_sqlite.sql")

# Guardar/leer datetime como texto ISO (evita el adaptador obsoleto de Python 3.12)
sqlite3.register_adapter(datetime, lambda d: d.isoformat(sep=" "))
sqlite3.register_converter("DATETIME", lambda b: datetime.fromisoformat(b.decode()))


class SQLiteRepository(BaseRepository):
    def __init__(self, db_path: str, table_name: str):
        super().__init__(table_name)
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        with open(_SCRIPT, encoding="utf-8") as fh, self.connect() as conn:
            conn.executescript(fh.read())

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            yield conn
        finally:
            conn.close()

    def _limit_sql(self, select_sql, limit):
        return f"{select_sql} LIMIT {int(limit)}"
