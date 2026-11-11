"""API REST de YakuTraza (Fase 1: datasets y control de calidad).

La documentación OpenAPI queda en /docs y /openapi.json; sirve como esquema
de intercambio para una futura integración con el SIA.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path as _Path
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
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from app.plazos.motor import EN_CURSO, MotorPlazos
from app.plazos.repositorio import expedientes_desde_bd

app = FastAPI(
    title="YakuTraza API",
    version="0.1.0",
    description=(
        "Trazabilidad verificable de trámites y recursos de inversión de las EPS. Prototipo para la Hackathon "
        "Sunass «Lideresas por el Agua», Desafío 3. Datos de muestra sintéticos (DS01–DS08); DS09 es real. "
        "Las reglas de plazo están «por validar» con la DRE. "
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


# ============================================================ Fase 2: plazos

ORDEN_ESTADO = {"vencido": 0, "no_calculable": 1, "por_vencer": 2, "en_plazo": 3, "incumplido": 4, "cumplido": 5}


class FeriadoOut(BaseModel):
    fecha: date
    nombre: str
    fuente: str


class DiferenciaCalendarioOut(BaseModel):
    fecha: date
    nombre: str
    en_libreria: bool
    en_supuestos: bool
    explicacion: str


class AlertaOut(BaseModel):
    expediente: str
    cod_eps: str
    reloj: str
    estado: str
    en_curso: bool
    titulo: str
    mensaje: str
    regla_id: str | None
    fuente: str
    estado_validacion: str
    respaldo: str | None
    hito: str | None
    etapa: str | None
    fecha_inicio: date | None
    fecha_limite: date | None
    plazo_dh: int | None
    dias_transcurridos: int | None
    dias_restantes: int | None
    documento_inicio: str | None
    documento_estado: str | None
    discrepancia: dict[str, Any] | None
    detalle: dict[str, Any]


def _rules(s: Settings) -> _Path:
    return _Path(s.rules_dir)


def _motor(s: Settings) -> MotorPlazos:
    return MotorPlazos(calendario_desde(_rules(s) / "feriados.yaml"), catalogo_desde(_rules(s) / "plazos.yaml"))


def _orden(a) -> tuple:
    return (ORDEN_ESTADO.get(a.estado, 9), a.dias_restantes if a.dias_restantes is not None else 10**6, a.expediente)


@app.get("/calendario/feriados", response_model=list[FeriadoOut], tags=["plazos"])
def feriados(anio: int = Query(..., ge=2018, le=2032), s: Settings = Depends(get_settings)):
    return [f.__dict__ for f in calendario_desde(_rules(s) / "feriados.yaml").feriados(anio)]


@app.get("/calendario/diferencias", response_model=list[DiferenciaCalendarioOut], tags=["plazos"])
def diferencias_calendario(s: Settings = Depends(get_settings)):
    return [d.__dict__ for d in calendario_desde(_rules(s) / "feriados.yaml").diferencias_con_supuestos()]


@app.get("/reglas/plazos", tags=["plazos"])
def reglas_plazos(s: Settings = Depends(get_settings)) -> dict[str, Any]:
    cat = catalogo_desde(_rules(s) / "plazos.yaml")
    return {
        "umbral_por_vencer_dh": cat.umbral_por_vencer,
        "fuentes_documentales": cat.documentos,
        "reglas": [{**r.__dict__, "fuente_texto": r.fuente_texto(cat.documentos)} for r in cat.reglas.values()],
    }


@app.get("/expedientes/{id_expediente}/relojes", response_model=list[AlertaOut], tags=["plazos"])
def relojes(id_expediente: str, fecha_corte: date | None = None, s: Settings = Depends(get_settings)):
    _lote(s)
    exps = expedientes_desde_bd(get_engine(s.database_url), id_expediente=id_expediente)
    if id_expediente not in exps:
        raise HTTPException(404, f"No existe el expediente {id_expediente} en DS02.")
    return [a.como_dict() for a in _motor(s).relojes(exps[id_expediente], fecha_corte or s.fecha_corte)]


@app.get("/alertas", response_model=list[AlertaOut], tags=["plazos"])
def alertas(
    fecha_corte: date | None = None,
    cod_eps: str | None = None,
    reloj: str | None = Query(None, description="normativo | interno | oficio"),
    solo_en_curso: bool = Query(True, description="Solo expedientes en trámite y alertas abiertas o no calculables"),
    s: Settings = Depends(get_settings),
):
    """Alertas ordenadas por plazo restante (vencidas primero), no por tamaño de la EPS."""
    _lote(s)
    corte = fecha_corte or s.fecha_corte
    motor = _motor(s)
    res = []
    for exp in expedientes_desde_bd(get_engine(s.database_url), cod_eps=cod_eps).values():
        if solo_en_curso and exp.estado != "en_tramite":
            continue
        for a in motor.relojes(exp, corte):
            if reloj and a.reloj != reloj:
                continue
            if solo_en_curso and a.estado not in EN_CURSO and a.estado != "no_calculable":
                continue
            res.append(a)
    return [a.como_dict() for a in sorted(res, key=_orden)]
