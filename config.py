"""Configuración central de la aplicación."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Motor de base de datos: "sqlserver" (el del parcial) o "sqlite" (para probar sin SQL Server)
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(BASE_DIR, "data", "deptmaintenance.db"))

SQLSERVER_CONN_STR = os.getenv(
    "SQLSERVER_CONN_STR",
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=deptmaintenance;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;",
)

TABLE_NAME = "tbl_sensors_data_temp"

# ---------------------------------------------------------------- Excel
DATA_SHEET = "Datos"
SENSORS_SHEET = "VALOR_SENSORES"      # bloque -> id_sensor (si no existe se usa DEFAULT_SENSORS)
DATE_COLUMN = "Fecha"
TIME_COLUMN = "Hora"
IGNORED_COLUMN_PREFIXES = ("EJEMPLO",)  # columnas de ejemplo del profesor

# Nombre de la variable en el encabezado -> data_type (char(4)).
# Se comparan sin tildes y en minúscula, así 'Rocío', 'Roció' y 'Rocio' son lo mismo.
VARIABLE_TO_DATA_TYPE = {
    "humedad": "RHUM",
    "punto rocio": "PURO",
    "radiacion par": "RASO",
    "temperatura": "TEMP",
}

# Respaldo si el Excel no trae la hoja VALOR_SENSORES. 'RESTO' = cualquier otro bloque.
DEFAULT_SENSORS = {"AG16": 62, "35": 63, "J8": 64, "SM5": 65, "RESTO": 0}

# data_value es NOT NULL. El paso 3 exige 4.689 x columnas registros, por eso las
# celdas vacías se cargan con este valor. Pon None para NO cargar celdas vacías.
EMPTY_VALUE = 0.0
