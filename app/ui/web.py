"""Responsabilidad única: interfaz web (Flask). Solo traduce HTTP <-> servicio."""
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from app.domain.models import MeasurementFilter, ValidationError

DATA_TYPE_LABELS = {"RHUM": "Humedad", "PURO": "Punto de rocío", "RASO": "Radiación PAR", "TEMP": "Temperatura"}


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        raise ValidationError(f"Fecha inválida: {value}")


def create_app(service) -> Flask:
    app = Flask(__name__)
    app.secret_key = "parcial-final-bi"
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

    @app.get("/")
    def index():
        rows, total, error = [], 0, None
        try:
            f = MeasurementFilter(
                fecha_inicio=_parse_date(request.args.get("fecha_inicio")),
                fecha_fin=_parse_date(request.args.get("fecha_fin")),
                block_name=request.args.get("block_name") or None,
                data_type=request.args.get("data_type") or None,
            )
            rows, total = service.search(f)
        except ValidationError as exc:
            error = str(exc)
        blocks, types = service.filter_options()
        return render_template("index.html", rows=rows, total=total, error=error,
                               blocks=blocks, types=types, labels=DATA_TYPE_LABELS, f=request.args)

    @app.post("/cargar")
    def upload():
        file = request.files.get("archivo")
        if not file or not file.filename:
            flash("Selecciona un archivo Excel.", "error")
        elif not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
            flash("El archivo debe ser Excel (.xlsx).", "error")
        else:
            try:
                r = service.load_excel(file, create_ip=(request.remote_addr or "")[:20])
                msg = (f"Carga exitosa: {r.excel_rows:,} filas × {r.measurement_columns} columnas = "
                       f"{r.inserted:,} registros en la tabla.").replace(",", ".")
                if r.empty_cells:
                    msg += f" {r.empty_cells:,} celdas vacías se cargaron con valor 0.".replace(",", ".")
                if r.skipped_rows:
                    n = r.skipped_rows
                    msg += (f" Se omitieron {n} filas de ejemplo (sin Fecha/Hora)." if n > 1
                            else " Se omitió 1 fila de ejemplo (sin Fecha/Hora).")
                msg += " Los datos del archivo anterior fueron reemplazados."
                flash(msg, "ok")
            except ValidationError as exc:
                flash(str(exc), "error")
        return redirect(url_for("index"))

    @app.errorhandler(413)
    def too_large(_):
        flash("El archivo supera los 50 MB.", "error")
        return redirect(url_for("index"))

    return app
