"""Repositorio SQL Server (motor del parcial). Requiere: pip install pyodbc
Crea antes la tabla con sql/00_create_table_tmp.sql (el script que les enviaron).
"""
from contextlib import contextmanager

from app.repositories.base_repository import BaseRepository


class SQLServerRepository(BaseRepository):
    def __init__(self, conn_str: str, table_name: str):
        super().__init__(table_name)
        import pyodbc  # solo se necesita si usas SQL Server
        self._pyodbc = pyodbc
        self.conn_str = conn_str

    @contextmanager
    def connect(self):
        conn = self._pyodbc.connect(self.conn_str, autocommit=False)
        try:
            yield conn
        finally:
            conn.close()

    def _prepare_cursor(self, cursor):
        cursor.fast_executemany = True  # 436 mil filas en segundos en vez de minutos

    def _clear_sql(self):
        return f"TRUNCATE TABLE dbo.{self.table}"  # más rápido que DELETE y también es transaccional

    def _limit_sql(self, select_sql, limit):
        return select_sql.replace("SELECT ", f"SELECT TOP ({int(limit)}) ", 1)
