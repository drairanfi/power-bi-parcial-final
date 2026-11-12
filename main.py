"""Punto de entrada: arma las dependencias (raíz de composición) y arranca la interfaz.

    python main.py                      -> SQLite (para probar)
    set DB_ENGINE=sqlserver & python main.py   -> SQL Server (Windows)
"""
import config
from app.domain.column_parser import ColumnParser
from app.services.excel_reader import ExcelReader
from app.services.load_service import LoadService
from app.ui.web import create_app


def build_repository():
    if config.DB_ENGINE == "sqlserver":
        from app.repositories.sqlserver_repository import SQLServerRepository
        return SQLServerRepository(config.SQLSERVER_CONN_STR, config.TABLE_NAME)
    from app.repositories.sqlite_repository import SQLiteRepository
    return SQLiteRepository(config.SQLITE_PATH, config.TABLE_NAME)


def build_service() -> LoadService:
    reader = ExcelReader(ColumnParser(config.VARIABLE_TO_DATA_TYPE), config)
    return LoadService(reader, build_repository(), config.EMPTY_VALUE)


if __name__ == "__main__":
    app = create_app(build_service())
    print(f"Base de datos: {config.DB_ENGINE}  ->  abre http://127.0.0.1:5000")
    app.run(debug=False)
