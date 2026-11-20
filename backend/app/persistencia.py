"""Guarda una carga (datos + hallazgos) y lee hallazgos de la base."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import delete, func, insert, inspect, select
from sqlalchemy.engine import Engine

from app import alcance
from app.calidad.base import Hallazgo
from app.db import TABLAS_DATASETS, calidad_hallazgos, carga_lotes, crear_esquema
from app.ingesta.cargar import Muestra


def guardar_carga(engine: Engine, muestra: Muestra, hallazgos: list[Hallazgo], fecha_corte: date,
                  hallazgos_mvp: list[Hallazgo] | None = None) -> int:
    """Reemplaza los datos cargados y agrega un lote nuevo con sus hallazgos.

    Los hallazgos de lotes anteriores se conservan (historia de cargas).
    """
    crear_esquema(engine)
    archivos = {n: {"filas": len(t.datos), "sha256": t.sha256} for n, t in muestra.tablas.items()}
    with engine.begin() as cx:
        lote_id = cx.execute(insert(carga_lotes).values(
            data_dir=str(muestra.data_dir), fecha_corte=fecha_corte, archivos=archivos, estado="cargado",
        )).inserted_primary_key[0]
        for nombre, tabla in TABLAS_DATASETS.items():
            cx.execute(delete(tabla))
            t = muestra.tablas.get(nombre)
            if t is None:
                continue
            columnas = [c.nombre for c in t.spec.columnas]
            filas = []
            for (idx, datos), (_, crudos) in zip(t.datos.iterrows(), t.crudos.iterrows()):
                fila = {c: datos[c] for c in columnas}
                fila.update(lote_id=lote_id, fila_origen=int(idx), valores_originales=crudos.to_dict())
                filas.append(fila)
            if filas:
                cx.execute(insert(tabla), filas)
        filas_h = _filas_hallazgos(lote_id, hallazgos, hallazgos_mvp)
        if filas_h:
            cx.execute(insert(calidad_hallazgos), filas_h)
    return lote_id


def ultimo_lote(engine: Engine) -> dict[str, Any] | None:
    if not inspect(engine).has_table(carga_lotes.name):
        return None  # base recién creada: todavía no se ejecutó `seed`
    with engine.connect() as cx:
        fila = cx.execute(select(carga_lotes).order_by(carga_lotes.c.id.desc()).limit(1)).mappings().first()
        return dict(fila) if fila else None


def _filas_hallazgos(lote_id: int, hallazgos: list[Hallazgo], hallazgos_mvp: list[Hallazgo] | None):
    return ([{**h.como_dict(), "lote_id": lote_id, "alcance": "muestra"} for h in hallazgos]
            + [{**h.como_dict(), "lote_id": lote_id, "alcance": "mvp"} for h in hallazgos_mvp or []])


def reemplazar_hallazgos(engine: Engine, lote_id: int, hallazgos: list[Hallazgo],
                         hallazgos_mvp: list[Hallazgo] | None = None) -> None:
    with engine.begin() as cx:
        cx.execute(delete(calidad_hallazgos).where(calidad_hallazgos.c.lote_id == lote_id))
        filas = _filas_hallazgos(lote_id, hallazgos, hallazgos_mvp)
        if filas:
            cx.execute(insert(calidad_hallazgos), filas)


def leer_hallazgos(engine: Engine, lote_id: int, **filtros: str | None) -> list[dict[str, Any]]:
    """Hallazgos del lote con el alcance de la solicitud: los del MVP en modo MVP, los de la muestra si no."""
    q = select(calidad_hallazgos).where(calidad_hallazgos.c.lote_id == lote_id,
                                        calidad_hallazgos.c.alcance == ("mvp" if alcance.modo_mvp() else "muestra"))
    for col, valor in filtros.items():
        if valor:
            q = q.where(calidad_hallazgos.c[col] == valor)
    q = q.order_by(calidad_hallazgos.c.id)
    with engine.connect() as cx:
        return [dict(r) for r in cx.execute(q).mappings()]


def contar_filas(engine: Engine) -> dict[str, int]:
    with engine.connect() as cx:
        return {n: cx.execute(select(func.count()).select_from(t)).scalar_one() for n, t in TABLAS_DATASETS.items()}
