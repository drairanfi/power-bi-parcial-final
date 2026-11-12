"""Casos de uso: cargar el Excel y consultar con filtros.

No sabe cómo se lee un Excel ni qué motor de base de datos se usa:
recibe esas piezas por inyección de dependencias (ver main.py).
"""
from app.domain.models import LoadResult, MeasurementFilter, ValidationError


class LoadService:
    def __init__(self, reader, repository, empty_value):
        self.reader = reader
        self.repository = repository
        self.empty_value = empty_value

    def load_excel(self, file, create_ip=None) -> LoadResult:
        data = self.reader.read(file)

        # Paso 3: total = filas del Excel x columnas de medición
        expected = data.valid_rows * len(data.columns)
        if self.empty_value is not None and len(data.records) != expected:
            raise ValidationError(f"Se esperaban {expected:,} registros y se generaron {len(data.records):,}.")

        inserted = self.repository.replace_all(data.records, create_ip)
        return LoadResult(
            excel_rows=data.valid_rows,
            measurement_columns=len(data.columns),
            inserted=inserted,
            empty_cells=data.empty_cells,
            skipped_rows=data.skipped_rows,
            columns=data.columns,
        )

    def search(self, filters: MeasurementFilter, limit: int = 500):
        if filters.fecha_inicio and filters.fecha_fin and filters.fecha_inicio > filters.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser mayor que la fecha fin.")
        return self.repository.find(filters, limit), self.repository.count(filters)

    def filter_options(self):
        return self.repository.distinct("block_name"), self.repository.distinct("data_type")
