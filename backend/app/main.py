"""API REST de YakuTraza (Fase 1: datasets y control de calidad).

La documentación OpenAPI queda en /docs y /openapi.json; sirve como esquema
de intercambio para una futura integración con el SIA.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import servicio
from app.calidad.base import ETIQUETA_TIPO, SEVERIDADES, TIPOS_ANUNCIADOS
from app.config import Settings, get_settings
from app.db import get_engine
from app.ingesta.especificacion import DATASETS, naturaleza_dataset
from app.persistencia import contar_filas, leer_hallazgos, ultimo_lote

app = FastAPI(
    title="YakuTraza API",
    version="0.1.0",
    description=(
        "Trazabilidad verificable de trámites y recursos de inversión de las EPS. Prototipo para la Hackathon "
        "Sunass «Lideresas por el Agua», Desafío 3. Datos de muestra sintéticos (DS01–DS08); DS09 es real. "
        "Ninguna salida es una decisión regulatoria."
    ),
    license_info={"name": "MIT"},
)


class ColumnaOut(BaseModel):
    nombre: str
    tipo: str
    unidad: str
    naturaleza: str
    nota: str


class DatasetOut(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    naturaleza: str
    llave: list[str]
    filas_cargadas: int | None
    columnas: list[ColumnaOut]


class HallazgoOut(BaseModel):
    id: int
    regla_id: str
    tipo: str
    severidad: str
    dataset: str
    fila: int | None
    llave: str | None
    titulo: str
    explicacion: str
    valor_observado: str | None
    valor_esperado: str | None
    fuente_regla: str
    estado_validacion: str
    detalle: dict[str, Any] | None


class TipoResumen(BaseModel):
    tipo: str
    etiqueta: str
    anunciado_en_diccionario: bool
    hallazgos: int
    por_severidad: dict[str, int]


class ResumenCalidad(BaseModel):
    lote_id: int
    fecha_corte: date
    total: int
    tipos: list[TipoResumen]


def _lote(s: Settings) -> dict[str, Any]:
    lote = ultimo_lote(get_engine(s.database_url))
    if lote is None:
        raise HTTPException(404, "Todavía no hay datos cargados. Ejecuta `seed`.")
    return lote


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"estado": "ok"}


@app.get("/datasets", response_model=list[DatasetOut], tags=["datos"])
def datasets(s: Settings = Depends(get_settings)):
    try:
        filas = contar_filas(get_engine(s.database_url))
    except Exception:  # base sin esquema todavía
        filas = {}
    return [
        DatasetOut(
            codigo=d.codigo, nombre=d.nombre, descripcion=d.descripcion, naturaleza=naturaleza_dataset(d),
            llave=list(d.llave), filas_cargadas=filas.get(d.nombre),
            columnas=[ColumnaOut(nombre=c.nombre, tipo=c.tipo, unidad=c.unidad, naturaleza=c.naturaleza, nota=c.nota)
                      for c in d.columnas],
        )
        for d in DATASETS
    ]


@app.get("/calidad/hallazgos", response_model=list[HallazgoOut], tags=["calidad"])
def hallazgos(
    tipo: str | None = Query(None, description="p. ej. duplicado, unidad_sospechosa, diferencia_mef"),
    severidad: str | None = Query(None, description=" | ".join(SEVERIDADES)),
    dataset: str | None = Query(None, description="nombre del CSV sin extensión"),
    regla_id: str | None = Query(None),
    s: Settings = Depends(get_settings),
):
    lote = _lote(s)
    return leer_hallazgos(get_engine(s.database_url), lote["id"], tipo=tipo, severidad=severidad,
                          dataset=dataset, regla_id=regla_id)


@app.get("/calidad/resumen", response_model=ResumenCalidad, tags=["calidad"])
def resumen(s: Settings = Depends(get_settings)):
    lote = _lote(s)
    hs = leer_hallazgos(get_engine(s.database_url), lote["id"])
    tipos = list(TIPOS_ANUNCIADOS) + sorted({h["tipo"] for h in hs} - set(TIPOS_ANUNCIADOS))
    return ResumenCalidad(
        lote_id=lote["id"], fecha_corte=lote["fecha_corte"], total=len(hs),
        tipos=[
            TipoResumen(
                tipo=t, etiqueta=ETIQUETA_TIPO.get(t, t), anunciado_en_diccionario=t in TIPOS_ANUNCIADOS,
                hallazgos=sum(1 for h in hs if h["tipo"] == t),
                por_severidad={sv: sum(1 for h in hs if h["tipo"] == t and h["severidad"] == sv) for sv in SEVERIDADES},
            )
            for t in tipos
        ],
    )


@app.get("/calidad/reporte.html", response_class=HTMLResponse, tags=["calidad"])
def reporte_html(descargar: bool = False, s: Settings = Depends(get_settings)):
    _lote(s)
    headers = {"Content-Disposition": 'attachment; filename="calidad.html"'} if descargar else None
    return HTMLResponse(servicio.html_reporte(s), headers=headers)
