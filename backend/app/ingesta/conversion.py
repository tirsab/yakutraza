"""Conversión de texto CSV a tipos del diccionario, sin corregir nada.

Si un valor no se puede convertir sin perder información, la conversión
devuelve None y un mensaje; el valor original se conserva en la carga y el
problema se registra como hallazgo de formato.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErrorConversion(ValueError):
    pass


def convertir(valor: str, tipo: str):
    """Convierte `valor` (texto del CSV) al `tipo` del diccionario.

    Celda vacía = dato no aplicable o no disponible (hoja Léame) -> None.
    """
    if valor is None or valor == "":
        return None
    if tipo == "texto":
        return valor
    if tipo == "entero":
        try:
            d = Decimal(valor)
        except InvalidOperation as e:
            raise ErrorConversion(f"«{valor}» no es un número entero") from e
        if d != d.to_integral_value():
            raise ErrorConversion(f"«{valor}» tiene decimales y el diccionario indica entero")
        return int(d)
    if tipo == "decimal":
        try:
            d = Decimal(valor)
        except InvalidOperation as e:
            raise ErrorConversion(f"«{valor}» no es un número decimal") from e
        if not d.is_finite():
            raise ErrorConversion(f"«{valor}» no es un número finito")
        return d
    if tipo == "fecha":
        if not _FECHA.match(valor):
            raise ErrorConversion(f"«{valor}» no tiene el formato AAAA-MM-DD")
        try:
            return date.fromisoformat(valor)
        except ValueError as e:
            raise ErrorConversion(f"«{valor}» no es una fecha válida") from e
    if tipo == "booleano":
        if valor == "True":
            return True
        if valor == "False":
            return False
        raise ErrorConversion(f"«{valor}» no es True ni False")
    raise ValueError(f"Tipo desconocido: {tipo}")
