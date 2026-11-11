"""Utilidades compartidas por las reglas."""

from __future__ import annotations

import calendar
import unicodedata
from datetime import date
from decimal import Decimal

import pandas as pd


def llave(fila: pd.Series, columnas) -> str:
    return " · ".join(str(fila[c]) if fila[c] not in (None, "") else "(vacío)" for c in columnas)


def trimestres(desde: str, hasta: str) -> list[str]:
    """Lista AAAA-Tn entre dos trimestres, inclusive."""
    a, q = int(desde[:4]), int(desde[-1])
    fin = (int(hasta[:4]), int(hasta[-1]))
    res = []
    while (a, q) <= fin:
        res.append(f"{a}-T{q}")
        a, q = (a + 1, 1) if q == 4 else (a, q + 1)
    return res


def meses(desde: str, hasta: str) -> list[str]:
    a, m = int(desde[:4]), int(desde[5:7])
    fin = (int(hasta[:4]), int(hasta[5:7]))
    res = []
    while (a, m) <= fin:
        res.append(f"{a}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return res


def fin_trimestre(t: str) -> date:
    a, q = int(t[:4]), int(t[-1])
    m = q * 3
    return date(a, m, calendar.monthrange(a, m)[1])


def fin_mes(am: str) -> date:
    a, m = int(am[:4]), int(am[5:7])
    return date(a, m, calendar.monthrange(a, m)[1])


def trimestre_anterior(t: str) -> str:
    a, q = int(t[:4]), int(t[-1])
    return f"{a - 1}-T4" if q == 1 else f"{a}-T{q - 1}"


def mes_anterior(am: str) -> str:
    a, m = int(am[:4]), int(am[5:7])
    return f"{a - 1}-12" if m == 1 else f"{a}-{m - 1:02d}"


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.upper().split())


def soles(v: Decimal | int | float | None) -> str:
    if v is None:
        return "(vacío)"
    d = Decimal(str(v)).quantize(Decimal("0.01"))
    entero, _, dec = f"{d:,.2f}".partition(".")
    return f"S/ {entero.replace(',', ' ')},{dec}"


def num(v: Decimal | int | float | None) -> str:
    if v is None:
        return "(vacío)"
    return format(Decimal(str(v)).normalize(), "f").replace(".", ",")


def rango_filas(filas: list[int], maximo: int = 12) -> str:
    filas = sorted(filas)
    if len(filas) <= maximo:
        return ", ".join(map(str, filas))
    return ", ".join(map(str, filas[:maximo])) + f" y {len(filas) - maximo} más"


def dec(x: float, decimales: int = 1) -> str:
    """Número con coma decimal (formato de la interfaz)."""
    return f"{x:.{decimales}f}".replace(".", ",")
