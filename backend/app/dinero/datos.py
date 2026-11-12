"""Lectura de los datasets cargados (base de datos) como DataFrames para la ruta del dinero."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.db import TABLAS_DATASETS, get_engine
from app.persistencia import ultimo_lote

NOMBRES = ("ds01_catalogo_eps", "ds02_procedimientos", "ds03_programa_inversiones", "ds04_ejecucion_inversiones",
           "ds05_fondo_inversiones_reservas", "ds06_estados_financieros", "ds08_inversiones_mef")


def _leer(engine: Engine, nombre: str) -> pd.DataFrame:
    t = TABLAS_DATASETS[nombre]
    with engine.connect() as cx:
        df = pd.DataFrame(cx.execute(select(t)).mappings().all())
    if df.empty:
        cols = [c.name for c in t.columns]
        df = pd.DataFrame(columns=cols)
    df = df.drop(columns=["valores_originales", "lote_id", "id"], errors="ignore").rename(columns={"fila_origen": "_fila"})
    return df.astype(object).where(df.notna(), None)


@lru_cache(maxsize=4)
def _cache(url: str, lote_id: int) -> dict[str, pd.DataFrame]:
    engine = get_engine(url)
    return {n: _leer(engine, n) for n in NOMBRES}


def tablas(url: str) -> dict[str, pd.DataFrame]:
    """Tablas de la última carga. Se guardan en memoria por lote: un `seed` nuevo invalida la caché."""
    lote = ultimo_lote(get_engine(url))
    if lote is None:
        raise LookupError("Todavía no hay datos cargados. Ejecuta `seed`.")
    return _cache(url, lote["id"])
