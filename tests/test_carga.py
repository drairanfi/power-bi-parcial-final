"""Pruebas: python -m pytest -q   (el Excel del parcial va en data/ParcialFinal_BI.xlsx)"""
import io
import os
import sys

import openpyxl
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from app.domain.column_parser import ColumnParser  # noqa: E402
from app.domain.models import MeasurementFilter, ValidationError  # noqa: E402
from app.repositories.sqlite_repository import SQLiteRepository  # noqa: E402
from app.services.excel_reader import ExcelReader  # noqa: E402
from app.services.load_service import LoadService  # noqa: E402

EXCEL = os.path.join(os.path.dirname(__file__), "..", "data", "ParcialFinal_BI.xlsx")
parser = ColumnParser(config.VARIABLE_TO_DATA_TYPE)


def make_service(tmp_path):
    repo = SQLiteRepository(str(tmp_path / "t.db"), config.TABLE_NAME)
    return LoadService(ExcelReader(parser, config), repo, config.EMPTY_VALUE)


def excel_bytes(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ------------------------------------------------------------ encabezados
@pytest.mark.parametrize("header, data_type, block", [
    ("Humedad AG10 - Betania %", "RHUM", "AG10"),
    ("Humedad B35\xa0DeRuiter - Betania %", "RHUM", "B35"),
    ("Punto Rocío  J4 Betania - Betania °C", "PURO", "J4"),
    ("Punto Roció AR 35 Betania - Betania °C", "PURO", "35"),
    ("Punto Rocio B40 Fuerte Betania - Betania °C", "PURO", "B40"),
    ("Radiación PAR SM5 - Betania µmol m-2 s-1", "RASO", "SM5"),
    ("Temperatura VLL3 - Betania °C", "TEMP", "VLL3"),
])
def test_parse_header_ok(header, data_type, block):
    info = parser.parse(header)
    assert (info.data_type, info.block_name) == (data_type, block)


@pytest.mark.parametrize("header", [
    "Humedad AG10 Betania %",      # sin ' - '
    "Humedad AG10 - Betania",      # sin unidad
    "Presión AG10 - Betania hPa",  # variable desconocida
    "Humedad - Betania %",         # sin bloque
    "Humedad ABC - Betania %",     # bloque sin número
])
def test_parse_header_error(header):
    with pytest.raises(ValidationError):
        parser.parse(header)


# ------------------------------------------------------- Excel del parcial
needs_excel = pytest.mark.skipif(not os.path.exists(EXCEL), reason="falta data/ParcialFinal_BI.xlsx")


@needs_excel
def test_parser_coincide_con_filas_de_ejemplo():
    raw = pd.read_excel(EXCEL, sheet_name="Datos", header=None, dtype=str, nrows=3)
    for col in raw.columns[2:]:
        header = raw.iloc[1, col]
        if pd.isna(header) or header.startswith("EJEMPLO"):
            continue
        info = parser.parse(header)
        assert info.block_name == raw.iloc[0, col], header
        assert info.data_type == raw.iloc[2, col], header


@needs_excel
def test_carga_completa(tmp_path):
    service = make_service(tmp_path)
    r = service.load_excel(EXCEL)
    assert (r.excel_rows, r.measurement_columns) == (4689, 93)
    assert r.inserted == 4689 * 93 == service.repository.count(MeasurementFilter())

    # Ejemplo de la columna EJEMPLO: (0,'RHUM',100,'2023-12-31 23:30:00','AG10') y (62,...,'AG16')
    rows, _ = service.search(MeasurementFilter(block_name="AG16", data_type="RHUM"), limit=1)
    assert rows[0]["data_date"] == "2023-12-31 23:30" and rows[0]["data_value"] == 100 and rows[0]["id_sensor"] == 62
    rows, _ = service.search(MeasurementFilter(block_name="AG10", data_type="RHUM"), limit=1)
    assert rows[0]["id_sensor"] == 0

    # Volver a cargar el mismo archivo no duplica
    service.load_excel(EXCEL)
    assert service.repository.count(MeasurementFilter()) == 4689 * 93

    # Filtro por fechas (fin inclusivo) + bloque + tipo
    _, total = service.search(MeasurementFilter(
        fecha_inicio=pd.Timestamp("2023-12-31").date(), fecha_fin=pd.Timestamp("2023-12-31").date(),
        block_name="AG10", data_type="RHUM"))
    assert total == 48  # cada 30 min el 31-dic


# ---------------------------------------------- filas de ejemplo opcionales
def test_sin_filas_de_ejemplo(tmp_path):
    f = excel_bytes([["Fecha", "Hora", "Humedad AG10 - Betania %", "Temperatura AG16 - Betania °C"],
                     ["2023-12-31", "23:30", "100", "12.5"],
                     ["2023-12-31", "23:00", "", "12.7"]])
    r = make_service(tmp_path).load_excel(f)
    assert (r.excel_rows, r.measurement_columns, r.inserted, r.empty_cells) == (2, 2, 4, 1)


def test_con_filas_de_ejemplo(tmp_path):
    f = excel_bytes([[None, None, "AG10"],
                     ["Fecha", "Hora", "Humedad AG10 - Betania %"],
                     [None, None, "RHUM"],
                     ["2023-12-31", "23:30", "100"]])
    r = make_service(tmp_path).load_excel(f)
    assert (r.excel_rows, r.inserted, r.skipped_rows) == (1, 1, 1)


def test_encabezado_invalido_muestra_error(tmp_path):
    f = excel_bytes([["Fecha", "Hora", "Humedad AG10 Betania"], ["2023-12-31", "23:30", "100"]])
    with pytest.raises(ValidationError, match="Humedad AG10 Betania"):
        make_service(tmp_path).load_excel(f)


def test_valor_no_numerico_muestra_error(tmp_path):
    f = excel_bytes([["Fecha", "Hora", "Humedad AG10 - Betania %"], ["2023-12-31", "23:30", "abc"]])
    with pytest.raises(ValidationError, match="no numérico"):
        make_service(tmp_path).load_excel(f)


def test_sin_columna_hora(tmp_path):
    f = excel_bytes([["Fecha", "Humedad AG10 - Betania %"], ["2023-12-31", "100"]])
    with pytest.raises(ValidationError, match="Hora"):
        make_service(tmp_path).load_excel(f)


# ------------------------------------- un Excel nuevo reemplaza al anterior
H = ["Fecha", "Hora", "Humedad AG10 - Betania %"]


def test_excel_nuevo_reemplaza_al_anterior(tmp_path):
    s = make_service(tmp_path)
    s.load_excel(excel_bytes([H, ["2023-12-31", "23:30", "100"], ["2023-12-31", "23:00", "99"]]))
    s.load_excel(excel_bytes([H, ["2024-01-05", "08:00", "55"]]))
    rows, total = s.search(MeasurementFilter())
    assert total == 1 and rows[0]["data_date"] == "2024-01-05 08:00"


def test_error_conserva_datos_anteriores(tmp_path):
    s = make_service(tmp_path)
    s.load_excel(excel_bytes([H, ["2023-12-31", "23:30", "100"]]))
    with pytest.raises(ValidationError):
        s.load_excel(excel_bytes([H, ["2024-01-05", "08:00", "abc"]]))
    assert s.repository.count(MeasurementFilter()) == 1


# ------------------------------------------------ formatos de fecha y hora
from datetime import datetime as _dt, time as _t, date as _d  # noqa: E402


@pytest.mark.parametrize("fecha, hora", [
    ("2023-12-31", "23:30"),
    ("31/12/2023", "23:30:00"),
    ("31/12/2023", "11:30 p. m."),
    ("31/12/2023", "11:30 PM"),
    ("2023-12-31 00:00:00", "1899-12-30 23:30:00"),
    (_dt(2023, 12, 31), _t(23, 30)),
    (_d(2023, 12, 31), "23:30"),
    (45291, 0.9791666667),          # serial de Excel + fracción de día
    ("45291", "0.9791666667"),
])
def test_formatos_fecha_hora(fecha, hora):
    assert ExcelReader._combine(fecha, hora) == _dt(2023, 12, 31, 23, 30)


def test_fecha_con_formato_raro_muestra_error(tmp_path):
    f = excel_bytes([H, ["2023-12-31", "23:30", "1"], ["31 de diciembre", "23:00", "2"]])
    with pytest.raises(ValidationError, match="Fila 3"):
        make_service(tmp_path).load_excel(f)
