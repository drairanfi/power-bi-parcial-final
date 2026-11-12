"""Responsabilidad única: interpretar los encabezados de medición.

Formato:  <Variable> <Bloque> [descripción] - <Ubicación> <Unidad>

    'Humedad AG10 - Betania %'                 -> RHUM / AG10
    'Punto Rocío B41 Fuerte Betania - Betania °C' -> PURO / B41
    'Radiación PAR SM5 - Betania µmol m-2 s-1'  -> RASO / SM5

El bloque es la primera palabra que contiene un número (así lo muestra la
fila de ejemplo del Excel: 'Punto Roció AR 35 ...' -> '35').
"""
import re
import unicodedata

from app.domain.models import ColumnInfo, ValidationError

_EXAMPLE = "'Humedad AG10 - Betania %'"


def normalize_spaces(text: str) -> str:
    """Quita espacios duros (\\xa0) y espacios repetidos."""
    return re.sub(r"\s+", " ", str(text).replace("\xa0", " ")).strip()


def _plain(text: str) -> str:
    """'Radiación PAR' -> 'radiacion par'."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class ColumnParser:
    def __init__(self, variable_map: dict):
        # Variables más largas primero para que 'punto rocio' gane a un posible 'punto'
        self._variables = sorted(variable_map.items(), key=lambda kv: -len(kv[0]))

    def parse(self, header) -> ColumnInfo:
        original = str(header)
        text = normalize_spaces(original)

        if " - " not in text:
            raise ValidationError(f"Columna '{original}': falta el separador ' - '. Formato esperado: {_EXAMPLE}.")
        left, right = (part.strip() for part in text.split(" - ", 1))

        right_tokens = right.split(" ", 1)
        if len(right_tokens) < 2:
            raise ValidationError(f"Columna '{original}': falta la ubicación o la unidad después de ' - '. Formato esperado: {_EXAMPLE}.")
        location, unit = right_tokens

        plain_left = _plain(left)
        for variable, data_type in self._variables:
            if plain_left == variable or plain_left.startswith(variable + " "):
                rest = left[len(variable):].split()
                break
        else:
            valid = ", ".join(v.title() for v, _ in self._variables)
            raise ValidationError(f"Columna '{original}': variable no reconocida. Válidas: {valid}.")

        block = next((tok for tok in rest if any(ch.isdigit() for ch in tok)), None)
        if block is None:
            raise ValidationError(f"Columna '{original}': no se encontró el bloque (ej. AG10). Formato esperado: {_EXAMPLE}.")

        return ColumnInfo(original, data_type, block.upper(), location, unit)
