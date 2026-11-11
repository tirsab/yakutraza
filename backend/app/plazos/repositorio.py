"""Construye expedientes del motor a partir de DS02 (muestra cargada o base de datos)."""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.db import TABLAS_DATASETS
from app.plazos.motor import Expediente, Hito


def _v(x):
    """None para vacíos (None, NaN o NaT de pandas)."""
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    if x is pd.NaT:
        return None
    return x


def _fecha(x) -> date | None:
    x = _v(x)
    if x is None:
        return None
    if isinstance(x, pd.Timestamp):
        return x.date()
    return x


def _entero(x) -> int | None:
    x = _v(x)
    return None if x is None else int(x)


def expedientes_desde_frames(procs: pd.DataFrame, hitos: pd.DataFrame,
                             fila_col: str = "_fila") -> dict[str, Expediente]:
    por_exp: dict[str, list[Hito]] = {}
    for _, h in hitos.iterrows():
        por_exp.setdefault(h["id_expediente"], []).append(Hito(
            nro=int(h["nro_hito"]), hito=h["hito"], etapa=_v(h["etapa"]), responsable=_v(h["responsable"]),
            fecha_inicio=_fecha(h["fecha_inicio"]), fecha_fin=_fecha(h["fecha_fin"]),
            plazo_referencial_dh=_entero(h["plazo_referencial_dh"]), plazo_etapa_dh=_entero(h["plazo_etapa_dh"]),
            cuenta_plazo=None if _v(h["cuenta_plazo"]) is None else bool(h["cuenta_plazo"]),
            documento=_v(h["documento"]), descripcion=_v(h["descripcion"]), fila=_entero(h.get(fila_col)),
        ))
    res = {}
    for _, p in procs.iterrows():
        res[p["id_expediente"]] = Expediente(
            id=p["id_expediente"], cod_eps=p["cod_eps"], tipo=p["tipo_procedimiento"],
            fecha_inicio=_fecha(p["fecha_inicio"]), plazo_maximo_dh=_entero(p["plazo_maximo_dh"]),
            estado=_v(p["estado"]), fecha_conclusion=_fecha(p["fecha_conclusion"]),
            fecha_limite_ds02=_fecha(p["fecha_limite"]), dias_suspension_ds02=_entero(p["dias_suspension_dh"]),
            dias_sunass_ds02=_entero(p["dias_habiles_sunass"]), hito_actual=_v(p["hito_actual"]),
            responsable_actual=_v(p["responsable_actual"]), fila=_entero(p.get(fila_col)),
            hitos=sorted(por_exp.get(p["id_expediente"], []), key=lambda h: h.nro),
        )
    return res


def expedientes_desde_muestra(muestra) -> dict[str, Expediente]:
    return expedientes_desde_frames(muestra["ds02_procedimientos"], muestra["ds02_hitos_procedimientos"])


def expedientes_desde_bd(engine: Engine, id_expediente: str | None = None,
                         cod_eps: str | None = None) -> dict[str, Expediente]:
    tp, th = TABLAS_DATASETS["ds02_procedimientos"], TABLAS_DATASETS["ds02_hitos_procedimientos"]
    qp, qh = select(tp), select(th)
    if id_expediente:
        qp, qh = qp.where(tp.c.id_expediente == id_expediente), qh.where(th.c.id_expediente == id_expediente)
    if cod_eps:
        qp = qp.where(tp.c.cod_eps == cod_eps)
    with engine.connect() as cx:
        procs = pd.DataFrame(cx.execute(qp).mappings().all())
        hitos = pd.DataFrame(cx.execute(qh).mappings().all())
    if procs.empty:
        return {}
    if hitos.empty:
        hitos = pd.DataFrame(columns=[c.name for c in th.columns])
    if cod_eps:
        hitos = hitos[hitos["id_expediente"].isin(set(procs["id_expediente"]))]
    procs = procs.astype(object).where(procs.notna(), None)
    hitos = hitos.astype(object).where(hitos.notna(), None)
    return expedientes_desde_frames(procs, hitos, fila_col="fila_origen")
