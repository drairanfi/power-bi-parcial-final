"""Entidades del dominio. No dependen de Excel, base de datos ni interfaz."""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


class ValidationError(Exception):
    """Error de validación del archivo o de sus datos (se muestra al usuario)."""


@dataclass(frozen=True)
class ColumnInfo:
    """Lo que se extrae de un encabezado como 'Humedad AG10 - Betania %'."""
    source_column: str
    data_type: str      # RHUM
    block_name: str     # AG10
    location: str       # Betania
    unit: str           # %


@dataclass
class LoadResult:
    """Resumen de una carga."""
    excel_rows: int
    measurement_columns: int
    inserted: int
    empty_cells: int
    skipped_rows: int
    columns: List[ColumnInfo] = field(default_factory=list)

    @property
    def expected(self) -> int:
        return self.excel_rows * self.measurement_columns


@dataclass
class MeasurementFilter:
    """Filtros de la interfaz."""
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    block_name: Optional[str] = None
    data_type: Optional[str] = None
