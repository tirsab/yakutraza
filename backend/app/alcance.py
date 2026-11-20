"""Modo MVP: qué EPS de la muestra se ven, con un solo filtro central al LEER los datos.

La base de datos conserva la muestra completa (20 EPS). Con MVP_EPS=EPS02,EPS07,EPS09, cada solicitud a la API ve solo
esas EPS, salvo que pida la muestra completa con el encabezado `X-Alcance: muestra` (el interruptor «Ver la muestra
completa» de la interfaz). Sin MVP_EPS, todo se ve como antes.

Los lectores que aplican el filtro: expedientes (plazos, bandeja, tablero, expediente vivo), tablas de la ruta del
dinero y de la vista ciudadana, filas de la vista ciudadana y hallazgos de calidad (que se evalúan dos veces en el
`seed`: con la muestra completa y solo con las EPS del MVP). Fuera de una solicitud (CLI, pruebas) se ve la muestra
completa.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import replace
from typing import Any, Iterable

import pandas as pd

# Los tres procedimientos del desafío: en modo MVP, la bandeja, el tablero y los indicadores muestran solo estos.
# Los reportes trimestrales, los reajustes por IPM y las verificaciones se ven en la ficha de cada EPS.
TIPOS_DESAFIO = frozenset({"cambio_programa_inversiones", "uso_excepcional_fondo", "revision_periodica"})
ENCABEZADO = "x-alcance"

_EPS: ContextVar[frozenset[str] | None] = ContextVar("eps_visibles", default=None)


def mvp_eps(texto: str | None) -> frozenset[str]:
    """«EPS02, EPS07,EPS09» → {"EPS02", "EPS07", "EPS09"}; vacío si no hay modo MVP."""
    return frozenset(x.strip().upper() for x in (texto or "").split(",") if x.strip())


def eps_visibles() -> frozenset[str] | None:
    """EPS que se ven en esta solicitud, o None si se ve la muestra completa."""
    return _EPS.get()


def modo_mvp() -> bool:
    return _EPS.get() is not None


def fijar(eps: Iterable[str] | None):
    """Fija el alcance (devuelve el token para `restaurar`). None = muestra completa."""
    return _EPS.set(frozenset(eps) if eps is not None else None)


def restaurar(token) -> None:
    _EPS.reset(token)


def visible(cod_eps: Any) -> bool:
    eps = _EPS.get()
    return eps is None or cod_eps is None or str(cod_eps) in eps


def tipo_en_vistas(tipo: str) -> bool:
    """En modo MVP, la bandeja, el tablero y los indicadores muestran solo los procedimientos del desafío."""
    return not modo_mvp() or tipo in TIPOS_DESAFIO


def filtrar_tablas(tablas: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Filtra DataFrames por cod_eps; DS08 por los CUI de los proyectos visibles (DS03). DS09 (IPM) es nacional."""
    eps = _EPS.get()
    if eps is None:
        return tablas
    out = {}
    cuis: set[str] = set()
    ds03 = tablas.get("ds03_programa_inversiones")
    if ds03 is not None and "cui" in ds03.columns:
        cuis = {str(c) for c in ds03[ds03["cod_eps"].isin(eps)]["cui"] if c not in (None, "")}
    for nombre, df in tablas.items():
        if "cod_eps" in df.columns:
            out[nombre] = df[df["cod_eps"].isin(eps)]
        elif "cui" in df.columns:
            out[nombre] = df[df["cui"].astype(str).isin(cuis)]
        else:
            out[nombre] = df
    return out


def filtrar_filas(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f for f in filas if visible(f.get("cod_eps"))]


def filtrar_muestra(muestra, eps: frozenset[str]):
    """Copia de la muestra solo con las EPS indicadas. Conserva la línea original del CSV (`_fila`), para que los
    hallazgos del modo MVP señalen las mismas filas que los de la muestra completa."""
    t = muestra.tablas
    ds02 = t.get("ds02_procedimientos")
    ids = set(ds02.datos.loc[ds02.datos["cod_eps"].isin(eps), "id_expediente"]) if ds02 is not None else set()
    ds03 = t.get("ds03_programa_inversiones")
    cuis = ({str(c) for c in ds03.datos.loc[ds03.datos["cod_eps"].isin(eps), "cui"] if c not in (None, "")}
            if ds03 is not None else set())
    tablas, filas_vistas = {}, {}
    for nombre, tc in t.items():
        d = tc.datos
        if "cod_eps" in d.columns:
            m = d["cod_eps"].isin(eps)
        elif "id_expediente" in d.columns:
            m = d["id_expediente"].isin(ids)
        elif "cui" in d.columns:
            m = d["cui"].astype(str).isin(cuis)
        else:
            m = pd.Series(True, index=d.index)
        tablas[nombre] = replace(tc, datos=d[m], crudos=tc.crudos[m])
        filas_vistas[nombre] = set(d.loc[m, "_fila"]) if "_fila" in d.columns else None
    problemas = [p for p in muestra.problemas
                 if p.fila is None or filas_vistas.get(p.dataset) is None or p.fila in filas_vistas[p.dataset]]
    return replace(muestra, tablas=tablas, problemas=problemas)


class MiddlewareAlcance:
    """Middleware ASGI: fija el alcance de cada solicitud según MVP_EPS y el encabezado X-Alcance."""

    def __init__(self, app, obtener_settings):
        self.app = app
        self.obtener_settings = obtener_settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        eps = mvp_eps(self.obtener_settings().mvp_eps)
        pide = dict(scope.get("headers") or []).get(ENCABEZADO.encode(), b"").decode().strip().lower()
        token = fijar(eps if eps and pide != "muestra" else None)
        try:
            await self.app(scope, receive, send)
        finally:
            restaurar(token)
