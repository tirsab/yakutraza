"""API de la Fase 4: ruta del dinero, contexto financiero y visibilidad."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.db import get_engine
from app.dinero import ruta
from app.dinero.ruta import a_json as _json
from app.dinero import visibilidad as vis
from app.dinero.datos import tablas
from app.expediente import vivo
from app.persistencia import leer_hallazgos, ultimo_lote
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde
from app.vistas.sesion import exige_vista

router = APIRouter(prefix="/ruta-dinero", tags=["ruta del dinero"], dependencies=[Depends(exige_vista("ruta_dinero"))])

router_contexto = APIRouter(tags=["ruta del dinero"])


@lru_cache
def _config(ruta_yaml: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta_yaml).read_text(encoding="utf-8"))


def _cfg(s: Settings) -> dict[str, Any]:
    return _config(Path(s.rules_dir) / "ruta_dinero.yaml")


def _vis(s: Settings) -> dict[str, Any]:
    return vis.catalogo(Path(s.rules_dir) / "visibilidad.yaml")


def _t(s: Settings):
    try:
        return tablas(s.database_url)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/resumen")
def resumen(cod_eps: str | None = None, anio: int | None = None, fondo: str | None = None,
            s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Totales por fondo o reserva: solicitado, autorizado, usado (ordinario, art. 89 y emergencia art. 90) y verificado."""
    t = _t(s)
    cfg = _cfg(s)
    r = ruta.resumen_fondos(t, cod_eps, anio, fondo, cfg["fondos"])
    r["categorias_uso"] = cfg["categorias_uso"]
    r["visibilidad"] = vis.mapa(_vis(s), "fondo")
    r["usos_emergencia"] = ruta.usos_emergencia(t, calendario_desde(Path(s.rules_dir) / "feriados.yaml"),
                                                catalogo_desde(Path(s.rules_dir) / "plazos.yaml"), cod_eps, anio)
    r["expedientes_uso"] = [ruta.ruta_expediente_uso(t, i, cfg["textos"])
                            for i in ruta._ufi(t, cod_eps, anio)["id_expediente"]]
    r["casos_reales"] = [x for x in (ruta.ruta_caso_real(c) for c in vivo.casos(s).values()) if x]
    r["filtros"] = {"cod_eps": sorted(set(t["ds05_fondo_inversiones_reservas"]["cod_eps"])),
                    "anios": sorted({int(m[:4]) for m in t["ds05_fondo_inversiones_reservas"]["anio_mes"]}),
                    "fondos": cfg["fondos"]}
    return _json(r)


@router.get("/fondos/{cod_eps}")
def fondos_eps(cod_eps: str, fondo: str | None = None, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    serie = ruta.serie_fondo(_t(s), cod_eps, fondo)
    if not serie:
        raise HTTPException(404, f"DS05 no tiene meses reportados para {cod_eps}.")
    return _json({"cod_eps": cod_eps, "serie": serie, "naturaleza": "sintético", "visibilidad": vis.mapa(_vis(s), "fondo"),
            "fuente": "DS05 ds05_fondo_inversiones_reservas"})


@router.get("/proyectos")
def lista_proyectos(cod_eps: str | None = None, fuente: str | None = None,
                    etapa: str | None = Query(None, description="peldaño actual de la escalera"),
                    periodo: str | None = Query(None, description="vigente | anterior"),
                    solo_senales: bool = False, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Programado frente a ejecutado por proyecto, con su escalera y la base del avance financiero."""
    cfg = _cfg(s)
    ps = ruta.proyectos(_t(s), cfg["parametros"], cfg["textos"], cod_eps=cod_eps, fuente=fuente, etapa=etapa,
                        solo_senales=solo_senales, periodo=periodo)
    return _json({"proyectos": ps, "total": len(ps), "umbral_senal_pp": cfg["parametros"]["umbral_senal_pp"]["valor"],
            "base_avance_financiero": cfg["parametros"]["base_avance_financiero"]["sustento"].strip(),
            "visibilidad": vis.mapa(_vis(s), "proyecto"), "escalera": cfg["escalera_proyecto"]})


@router.get("/proyectos/{cod_proyecto}")
def proyecto(cod_proyecto: str, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    cfg = _cfg(s)
    p = ruta.detalle_proyecto(_t(s), cfg["parametros"], cfg["textos"], cod_proyecto)
    if p is None:
        raise HTTPException(404, f"No existe el proyecto {cod_proyecto} en DS03.")
    p["visibilidad"] = vis.mapa(_vis(s), "proyecto")
    p["vista_publica"] = vis.solo_publico(_vis(s), "proyecto", p)
    return _json(p)


@router.get("/expedientes/{id_expediente}")
def expediente(id_expediente: str, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Escalera solicitado → autorizado (fondo o reserva) → usado → verificación posterior → devolución."""
    caso = vivo.casos(s).get(id_expediente)
    r = ruta.ruta_caso_real(caso) if caso else ruta.ruta_expediente_uso(_t(s), id_expediente, _cfg(s)["textos"])
    if r is None:
        raise HTTPException(404, f"No hay ruta del dinero para {id_expediente}.")
    r["visibilidad"] = vis.mapa(_vis(s), "expediente_uso_fondo")
    return _json(r)


@router_contexto.get("/contexto-financiero/{cod_eps}", dependencies=[Depends(exige_vista("ruta_dinero"))])
def contexto(cod_eps: str, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Indicadores de DS06 como contexto (nunca nota ni diagnóstico), con avisos del control de calidad."""
    t = _t(s)
    lote = ultimo_lote(get_engine(s.database_url))
    r = ruta.contexto_financiero(t, cod_eps, leer_hallazgos(get_engine(s.database_url), lote["id"]))
    if not r["anios"]:
        raise HTTPException(404, f"DS06 no tiene estados financieros de {cod_eps}.")
    r["visibilidad"] = vis.mapa(_vis(s), "contexto_financiero")
    return _json(r)


@router_contexto.get("/visibilidad")
def visibilidad(s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Catálogo de visibilidad: qué dato podrá mostrar la vista ciudadana (público) y cuál no (reservado)."""
    return _vis(s)
