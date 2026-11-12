"""Responsabilidad única: leer el Excel y dejarlo como tabla larga lista para insertar.

 1. Concatena Fecha + Hora -> data_date
 2. Extrae data_type y block_name de cada encabezado (ColumnParser)
 3. Pasa de formato ancho (una columna por sensor) a largo (una fila por valor)

Las filas de ejemplo (la de bloques 'AG10...' y la de tipos 'RHUM...') pueden
venir o no: se detecta la fila de encabezados y se omiten las filas sin Fecha/Hora.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List

import pandas as pd

from app.domain.column_parser import ColumnParser, normalize_spaces
from app.domain.models import ColumnInfo, ValidationError

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")
_TIME_FORMATS = ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p")


@dataclass
class ExcelData:
    records: pd.DataFrame        # data_date, data_type, block_name, id_sensor, data_value
    columns: List[ColumnInfo]
    valid_rows: int
    skipped_rows: int
    empty_cells: int


class ExcelReader:
    def __init__(self, parser: ColumnParser, cfg):
        self.parser = parser
        self.cfg = cfg

    # ------------------------------------------------------------------ público
    def read(self, file) -> ExcelData:
        sheets = self._open(file)
        df = self._data_frame(sheets)
        columns = self._parse_columns(df)
        sensors = self._sensor_map(sheets)

        df["data_date"] = [self._combine(f, h) for f, h in zip(df[self.cfg.DATE_COLUMN], df[self.cfg.TIME_COLUMN])]
        valid = df[df["data_date"].notna()]
        skipped = len(df) - len(valid)
        if valid.empty:
            raise ValidationError("El archivo no tiene filas con Fecha y Hora válidas.")

        values = valid[[c.source_column for c in columns]].apply(self._to_number)
        self._check_numbers(valid, values, columns)

        long = values.assign(data_date=valid["data_date"]).melt(
            id_vars="data_date", var_name="source_column", value_name="data_value")
        empty_cells = int(long["data_value"].isna().sum())

        info = pd.DataFrame([{"source_column": c.source_column, "data_type": c.data_type,
                              "block_name": c.block_name} for c in columns])
        long = long.merge(info, on="source_column").drop(columns="source_column")
        long["id_sensor"] = long["block_name"].map(lambda b: sensors.get(b, sensors.get("RESTO", 0))).astype(int)

        if self.cfg.EMPTY_VALUE is None:
            long = long.dropna(subset=["data_value"])
        else:
            long["data_value"] = long["data_value"].fillna(self.cfg.EMPTY_VALUE)

        return ExcelData(long, columns, len(valid), skipped, empty_cells)

    # ----------------------------------------------------------------- privado
    def _open(self, file) -> Dict[str, pd.DataFrame]:
        try:
            return pd.read_excel(file, sheet_name=None, header=None, dtype=object)
        except Exception as exc:
            raise ValidationError(f"No se pudo leer el archivo Excel: {exc}") from exc

    def _data_frame(self, sheets) -> pd.DataFrame:
        raw = sheets.get(self.cfg.DATA_SHEET, next(iter(sheets.values())))
        header_row = self._find_header_row(raw)
        df = raw.iloc[header_row + 1:].copy()
        df.columns = [normalize_spaces(c) if pd.notna(c) else "" for c in raw.iloc[header_row]]

        keep = [c for c in df.columns if c and not c.upper().startswith(self.cfg.IGNORED_COLUMN_PREFIXES)]
        if len(set(keep)) != len(keep):
            dup = sorted({c for c in keep if keep.count(c) > 1})
            raise ValidationError(f"Hay columnas repetidas: {', '.join(dup)}.")
        return df[keep].dropna(how="all")

    def _find_header_row(self, raw: pd.DataFrame) -> int:
        wanted = {self.cfg.DATE_COLUMN.lower(), self.cfg.TIME_COLUMN.lower()}
        for i in range(min(10, len(raw))):
            cells = {str(v).strip().lower() for v in raw.iloc[i] if pd.notna(v)}
            if wanted <= cells:
                return i
        raise ValidationError(
            f"No se encontró la fila de encabezados con las columnas '{self.cfg.DATE_COLUMN}' y '{self.cfg.TIME_COLUMN}'.")

    def _parse_columns(self, df) -> List[ColumnInfo]:
        headers = [c for c in df.columns if c not in (self.cfg.DATE_COLUMN, self.cfg.TIME_COLUMN)]
        if not headers:
            raise ValidationError("El Excel no tiene columnas de medición (ej. 'Humedad AG10 - Betania %').")
        columns, errors = [], []
        for h in headers:
            try:
                columns.append(self.parser.parse(h))
            except ValidationError as exc:
                errors.append(str(exc))
        if errors:
            raise ValidationError("Encabezados con formato inválido:\n" + "\n".join(errors))
        return columns

    def _sensor_map(self, sheets) -> Dict[str, int]:
        sheet = sheets.get(self.cfg.SENSORS_SHEET)
        if sheet is None:
            return dict(self.cfg.DEFAULT_SENSORS)
        mapping = {}
        for dato, id_sensor in sheet.iloc[1:, :2].dropna().itertuples(index=False):
            try:
                mapping[str(dato).strip().upper()] = int(id_sensor)
            except (TypeError, ValueError):
                raise ValidationError(f"Hoja {self.cfg.SENSORS_SHEET}: ID_SENSOR inválido para '{dato}'.")
        return mapping or dict(self.cfg.DEFAULT_SENSORS)

    @staticmethod
    def _to_number(col: pd.Series) -> pd.Series:
        cleaned = col.map(lambda v: None if pd.isna(v) or str(v).strip() == "" else str(v).strip().replace(",", "."))
        return pd.to_numeric(cleaned, errors="coerce").where(cleaned.notna(), None).astype(float)

    @staticmethod
    def _check_numbers(original, numbers, columns):
        """Error si una celda tiene texto que no es número (ej. 'abc')."""
        errors = []
        for c in columns:
            raw = original[c.source_column]
            bad = numbers[c.source_column].isna() & raw.notna() & (raw.astype(str).str.strip() != "")
            for idx in bad[bad].index[:3]:
                errors.append(f"Fila {idx + 1}, columna '{c.source_column}': valor no numérico '{raw[idx]}'.")
        if errors:
            raise ValidationError("Valores inválidos:\n" + "\n".join(errors[:15]))

    @staticmethod
    def _combine(fecha, hora):
        """Concatena Fecha + Hora en un datetime. None si alguna no es válida."""
        d, t = ExcelReader._to_date(fecha), ExcelReader._to_time(hora)
        return datetime.combine(d, t) if d and t is not None else None

    @staticmethod
    def _to_date(v):
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if v is None or pd.isna(v):
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(str(v).strip()[:10], fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _to_time(v):
        if isinstance(v, datetime):
            return v.time()
        if isinstance(v, time):
            return v
        if v is None or pd.isna(v):
            return None
        if isinstance(v, (int, float)) and 0 <= v < 1:  # hora guardada como fracción de día
            return (datetime.min + timedelta(days=float(v))).time().replace(microsecond=0)
        for fmt in _TIME_FORMATS:
            try:
                return datetime.strptime(str(v).strip(), fmt).time()
            except ValueError:
                continue
        return None
