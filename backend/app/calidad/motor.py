"""Ejecuta el catálogo de reglas sobre una muestra cargada."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.calidad.base import SEVERIDADES, Contexto, Hallazgo, cargar_catalogo
from app.calidad.reglas import REGISTRO, cargar_modulos
from app.ingesta.cargar import Muestra

ORDEN_SEVERIDAD = {s: i for i, s in enumerate(SEVERIDADES)}


def evaluar(muestra: Muestra, ruta_catalogo: Path, fecha_corte: date) -> list[Hallazgo]:
    cargar_modulos()
    catalogo = cargar_catalogo(ruta_catalogo)
    sin_logica = [rid for rid in catalogo if rid not in REGISTRO]
    if sin_logica:
        raise ValueError(f"Reglas del catálogo sin implementación: {sin_logica}")
    ctx = Contexto(fecha_corte=fecha_corte, reglas=catalogo)
    hallazgos: list[Hallazgo] = []
    for rid, cfg in catalogo.items():
        if cfg.activa:
            hallazgos.extend(REGISTRO[rid](muestra, cfg, ctx))
    hallazgos.sort(key=lambda h: (ORDEN_SEVERIDAD[h.severidad], h.tipo, h.dataset, h.fila or 0, h.regla_id))
    return hallazgos
