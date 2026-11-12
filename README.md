# Carga de datos de sensores (Parcial Final BI)

Carga `ParcialFinal_BI.xlsx` a la tabla `dbo.tbl_sensors_data_temp` y la consulta desde una interfaz web con filtros.

## Cómo correrlo

```bash
pip install -r requirements.txt
python main.py            # abre http://127.0.0.1:5000
```

Por defecto usa **SQLite** (archivo `data/deptmaintenance.db`), así puedes probar sin instalar nada más.

### Con SQL Server (el motor del parcial)

1. Ejecuta `sql/00_create_table_tmp.sql` en SSMS (crea `tbl_sensors_data_temp` en `deptmaintenance`).
2. Instala el *ODBC Driver 17 o 18 for SQL Server* y `pip install pyodbc`.
3. Revisa la cadena de conexión en `config.py` (`SQLSERVER_CONN_STR`) y arranca:

```bat
set DB_ENGINE=sqlserver
python main.py
```

## Qué hace (pasos del enunciado)

| Paso | Dónde |
|---|---|
| 1. Concatenar `Fecha` + `Hora` → `data_date` | `ExcelReader._combine` |
| 2. De `Humedad AG10 - Betania %` sacar `RHUM` → `data_type` y `AG10` → `block_name` | `ColumnParser.parse` |
| 3. Registros finales = 4.689 × columnas (4.689 × 93 = **436.077**) | `LoadService.load_excel` (lo valida) |
| 4. Interfaz con filtros `fecha_inicio`, `fecha_fin`, `block_name`, `data_type` | `app/ui/web.py` + `templates/index.html` |

Tipos de dato detectados en los encabezados:

| Encabezado empieza por | data_type |
|---|---|
| Humedad | RHUM |
| Punto Rocío (también "Roció", "Rocio") | PURO |
| Radiación PAR | RASO |
| Temperatura | TEMP |

`id_sensor` sale de la hoja `VALOR_SENSORES` (AG16→62, 35→63, J8→64, SM5→65, el resto→0).

## Validaciones (errores que ve el usuario)

- Encabezado sin el formato `<Variable> <Bloque> - <Ubicación> <Unidad>` (ej. `Humedad AG10 Betania %`).
- Variable desconocida (ej. `Presión AG10 - Betania hPa`) o bloque sin número.
- Faltan las columnas `Fecha` u `Hora`, hay columnas repetidas o un valor no numérico (ej. `abc`).
- Fecha de inicio mayor que la fecha fin en los filtros.

Las filas de ejemplo (fila 1 con los bloques `AG10…` y fila 3 con `RHUM…`) pueden venir o no: el programa
busca la fila de encabezados y omite las filas sin Fecha/Hora. Las columnas `EJEMPLO_*` se ignoran.

## Decisiones a tener en cuenta

- **Celdas vacías → 0.** El Excel tiene 208.306 celdas vacías y `data_value` es `NOT NULL`. Para cumplir el
  paso 3 (4.689 × columnas) se cargan como 0. Si prefieres no cargarlas, pon `EMPTY_VALUE = None` en `config.py`.
- **Recargar no duplica.** Si subes el mismo archivo otra vez, se borran los datos del mismo periodo y
  tipos y se insertan de nuevo, todo en una sola transacción.
- `create_date` = fecha de la carga y `create_ip` = IP de quien subió el archivo.

## Estructura (responsabilidades separadas)

```
main.py                       raíz de composición: arma las piezas y arranca
config.py                     configuración (motor, tabla, mapeos)
app/domain/models.py          entidades y ValidationError
app/domain/column_parser.py   interpreta encabezados -> data_type / block_name
app/services/excel_reader.py  lee el Excel, concatena fecha+hora, ancho -> largo
app/services/load_service.py  casos de uso: cargar y consultar
app/repositories/             persistencia (base + SQLite + SQL Server)
app/ui/                       interfaz web Flask
sql/                          scripts de la tabla
tests/test_carga.py           pruebas (python -m pytest -q)
```
