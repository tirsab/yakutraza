"""API de la Fase 5: sesión de la demo, etiquetas, bandeja, tablero gerencial, simulador,
vista EPS, vista ciudadana y resúmenes en quechua."""

from __future__ import annotations

from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import insert, select, update

from app.config import Settings, get_settings
from app.db import get_engine, resumenes_quechua
from app.dinero import visibilidad as vis
from app.dinero.datos import tablas
from app.dinero.ruta import a_json
from app.expediente import bitacora
from app.expediente.usuarios import ErrorPermiso, Usuario, exigir, roles_desde, usuarios_desde
from app.persistencia import ultimo_lote
from app.vistas import bandeja as bandeja_srv
from app.vistas import ciudadana, eps, tablero
from app.vistas.etiquetas import catalogo as catalogo_etiquetas
from app.vistas.sesion import exige_vista, ruta_usuarios, sesion

router = APIRouter()


@lru_cache
def _ruta_dinero(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def _cfg_dinero(s: Settings) -> dict[str, Any]:
    return _ruta_dinero(Path(s.rules_dir) / "ruta_dinero.yaml")


def _etq(s: Settings) -> dict[str, Any]:
    return catalogo_etiquetas(Path(s.rules_dir) / "etiquetas.yaml")


def _vis(s: Settings) -> dict[str, Any]:
    return vis.catalogo(Path(s.rules_dir) / "visibilidad.yaml")


def _carga(s: Settings) -> None:
    if ultimo_lote(get_engine(s.database_url)) is None:
        raise HTTPException(404, "Todavía no hay datos cargados. Ejecuta `seed`.")


def _ctx(s: Settings, fecha_corte: date | None) -> tablero.Contexto:
    _carga(s)
    ctx = tablero.contexto(get_engine(s.database_url), s, fecha_corte)
    minimo = _corte_min(ctx)
    if fecha_corte is not None and not (minimo <= fecha_corte <= s.fecha_corte):
        raise HTTPException(422, f"La fecha de corte debe estar entre el {minimo:%d-%m-%Y} y el "
                                 f"{s.fecha_corte:%d-%m-%Y} (fecha de corte de la muestra): después no hay datos.")
    return ctx


def _corte_min(ctx: tablero.Contexto) -> date:
    fechas = [e.fecha_inicio for e in ctx.exps.values() if e.fecha_inicio]
    return min(fechas) if fechas else ctx.s.fecha_corte


# ------------------------------------------------------------------ sesión
@router.get("/config", tags=["sesión"])
def config(s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Configuración de la interfaz: modo demo, fecha de corte y opciones del selector «Ver como»."""
    roles = roles_desde(Path(s.rules_dir) / "roles.yaml")
    eng = get_engine(s.database_url)
    lote = ultimo_lote(eng)
    eps_lista, minimo = [], s.fecha_corte
    if lote is not None:
        ctx = tablero.contexto(eng, s)
        minimo = _corte_min(ctx)
        t = tablas(s.database_url)
        eps_lista = [{"cod_eps": r["cod_eps"], "nombre_eps": r["nombre_eps"]}
                     for _, r in t["ds01_catalogo_eps"].sort_values("cod_eps").iterrows()]
    usuarios = usuarios_desde(ruta_usuarios(s)) if s.modo_demo else {}
    por_rol = {}
    for u in usuarios.values():
        por_rol.setdefault(u.rol, u.id)
    return {
        "modo_demo": s.modo_demo,
        "fecha_corte_muestra": s.fecha_corte, "corte_min": minimo, "corte_max": s.fecha_corte,
        "rotulo": "Prototipo con datos sintéticos de la muestra del Hackathon Sunass",
        "roles": [{"rol": k, "nombre": r["nombre"], "inicio": r["inicio"], "vistas": r["vistas"],
                   "usuario": por_rol.get(k) if k not in ("eps", "ciudadania") else None}
                  for k, r in roles.items() if s.modo_demo or k == "ciudadania"],
        "eps": eps_lista if s.modo_demo else [],
    }


@router.get("/sesion", tags=["sesión"])
def leer_sesion(u: Usuario = Depends(sesion)) -> dict[str, Any]:
    return u.como_dict()


@router.get("/etiquetas", tags=["sesión"])
def etiquetas(s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Etiquetas en lenguaje claro para cada código de la muestra (rules/etiquetas.yaml)."""
    return _etq(s)


# ----------------------------------------------------------------- bandeja
@router.get("/bandeja", tags=["bandeja"])
def bandeja(fecha_corte: date | None = None, especialista: str | None = None,
            u: Usuario = Depends(exige_vista("bandeja")), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """«Mi siguiente acción»: ordenada por plazo restante, con qué requiere acción, qué falta y por qué importa."""
    ctx = _ctx(s, fecha_corte)
    if u.rol == "especialista_srt":
        especialista = u.id
    filas = tablero.filtrar(tablero.evaluar(ctx), especialista=especialista)
    xs = bandeja_srv.items(ctx, filas, _etq(s))
    xs += [x for x in bandeja_srv.items_casos_reales(ctx, ctx.especialistas)
           if not especialista or x["especialista"] == especialista]
    xs = bandeja_srv.ordenar(xs)
    return a_json({"fecha_corte": ctx.corte, "especialista": especialista, "items": xs,
                   "resumen": {e: sum(1 for x in xs if x["estado"] == e) for e in tablero.ESTADOS},
                   "rotulo_asignacion": ctx.cfg["asignacion"]["rotulo"],
                   "orden": "Por plazo restante: vencidos primero, luego «no puedo calcular», por vencer y en plazo."})


# ----------------------------------------------------------------- tablero
@router.get("/tablero", tags=["tablero gerencial"])
def ver_tablero(fecha_corte: date | None = None, tipo: str | None = None, cod_eps: str | None = None,
                responsable: str | None = None, especialista: str | None = None, estado: str | None = None,
                u: Usuario = Depends(exige_vista("tablero")), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Indicadores a la fecha de corte; cada indicador trae los ids para llegar hasta el expediente."""
    ctx = _ctx(s, fecha_corte)
    todas = tablero.evaluar(ctx)
    sin_estado = tablero.filtrar(todas, tipo=tipo, cod_eps=cod_eps, responsable=responsable, especialista=especialista)
    filas = tablero.filtrar(sin_estado, estado=estado)
    return a_json({
        "fecha_corte": ctx.corte, "fecha_corte_muestra": s.fecha_corte, "corte_min": _corte_min(ctx),
        "filtros_aplicados": {"tipo": tipo, "cod_eps": cod_eps, "responsable": responsable,
                              "especialista": especialista, "estado": estado},
        "opciones": {"tipo": sorted({e.tipo for e in ctx.exps.values()}),
                     "cod_eps": sorted({e.cod_eps for e in ctx.exps.values()}),
                     "responsable": sorted({h.responsable for e in ctx.exps.values() for h in e.hitos if h.responsable}),
                     "especialista": ctx.especialistas, "estado": list(tablero.ESTADOS)},
        "indicadores": tablero.indicadores(sin_estado),
        "expedientes": [f.como_dict() for f in filas],
        "supera_plazo": tablero.supera_plazo(ctx, cod_eps=cod_eps, tipo=tipo),
        "cuellos": tablero.cuellos(ctx, tipo=tipo, cod_eps=cod_eps),
        "embudo": tablero.embudo(ctx, tipo=tipo, cod_eps=cod_eps),
        "carga": tablero.carga(ctx, tablero.filtrar(todas, tipo=tipo, cod_eps=cod_eps)),
        "calidad": tablero.resumen_calidad(ctx.engine),
        "naturaleza": "sintético",
    })


class EscenarioIn(BaseModel):
    fecha_corte: date | None = None
    dias_sin_accion: int = Field(0, ge=0, le=120)
    umbral_por_vencer_dh: int | None = Field(None, ge=0, le=30)
    especialistas_adicionales: int = Field(0, ge=0, le=10)
    tipo: str | None = None
    cod_eps: str | None = None


@router.post("/simulador", tags=["tablero gerencial"])
def simulador(e: EscenarioIn, u: Usuario = Depends(exige_vista("simulador")),
              s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Escenarios «¿qué pasaría si…?». Calcula en memoria: nunca modifica los datos reales."""
    ctx = _ctx(s, e.fecha_corte)
    return a_json(tablero.simular(ctx, dias_sin_accion=e.dias_sin_accion, umbral_por_vencer_dh=e.umbral_por_vencer_dh,
                                  especialistas_adicionales=e.especialistas_adicionales,
                                  filtros={"tipo": e.tipo, "cod_eps": e.cod_eps}))


# --------------------------------------------------------------------- EPS
@router.get("/mi-eps", tags=["vista EPS"])
def mi_eps(fecha_corte: date | None = None, u: Usuario = Depends(exige_vista("mi_eps")),
           s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Sus trámites, qué le falta y hasta cuándo, y su fondo. Sin documentos internos de Sunass."""
    ctx = _ctx(s, fecha_corte)
    return a_json(eps.resumen_eps(ctx, u.cod_eps, _etq(s), _cfg_dinero(s)["textos"]))


# --------------------------------------------------------------- ciudadana
@router.get("/publico/localidades", tags=["vista ciudadana"])
def buscar_localidades(q: str = Query(..., min_length=2), s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    """Búsqueda por localidad, ubigeo, distrito, provincia o departamento. Solo campos públicos."""
    _carga(s)
    return a_json(ciudadana.buscar(get_engine(s.database_url), _vis(s), q))


@router.get("/publico/localidades/{ubigeo}", tags=["vista ciudadana"])
def ver_localidad(ubigeo: str, fecha_corte: date | None = None, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Proyectos con su etapa, población (estimada), decisión de Sunass vinculada y audiencias públicas."""
    ctx = _ctx(s, fecha_corte)
    cfg = _cfg_dinero(s)
    r = ciudadana.localidad(ctx.engine, _vis(s), tablas(s.database_url), cfg["parametros"], cfg["textos"], ctx.exps,
                            ubigeo, ctx.corte)
    if r is None:
        raise HTTPException(404, f"No hay una localidad con ubigeo {ubigeo} en la muestra.")
    return a_json(r)


# --------------------------------------------------------- resumen en quechua
class ResumenIn(BaseModel):
    ubigeo: str
    texto: str = Field(..., min_length=10)
    texto_castellano: str | None = None


def _exigir(u: Usuario, permiso: str) -> None:
    try:
        exigir(u, permiso)
    except ErrorPermiso as e:
        raise HTTPException(401 if u.es_ciudadania else 403, str(e)) from e


@router.get("/resumenes-quechua", tags=["vista ciudadana"])
def listar_resumenes(ubigeo: str | None = None, u: Usuario = Depends(sesion),
                     s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    if not u.es_sunass:
        raise HTTPException(403, "Solo el personal de Sunass ve los resúmenes por validar.")
    q = select(resumenes_quechua).order_by(resumenes_quechua.c.id.desc())
    if ubigeo:
        q = q.where(resumenes_quechua.c.ubigeo == ubigeo)
    with get_engine(s.database_url).connect() as cx:
        return [dict(r) for r in cx.execute(q).mappings()]


@router.post("/resumenes-quechua", status_code=201, tags=["vista ciudadana"])
def proponer_resumen(r: ResumenIn, u: Usuario = Depends(sesion), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Una persona escribe el resumen en quechua. Queda «propuesto»: no se publica hasta que otra lo valida."""
    _exigir(u, "proponer_resumen_quechua")
    fila = {"ubigeo": r.ubigeo, "texto": r.texto.strip(), "texto_castellano": r.texto_castellano, "estado": "propuesto",
            "propuesto_por": u.id, "propuesto_en": datetime.now(timezone.utc)}
    with get_engine(s.database_url).begin() as cx:
        rid = cx.execute(insert(resumenes_quechua).values(**fila)).inserted_primary_key[0]
        bitacora.registrar(cx, u, "proponer_resumen_quechua", "resumen_quechua", str(rid),
                           despues={"ubigeo": r.ubigeo, "estado": "propuesto"})
    return {"id": rid, "estado": "propuesto"}


@router.post("/resumenes-quechua/{rid}/validar", tags=["vista ciudadana"])
def validar_resumen(rid: int, u: Usuario = Depends(sesion), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Valida un resumen propuesto por otra persona. Recién entonces se publica en la vista ciudadana."""
    _exigir(u, "validar_resumen_quechua")
    with get_engine(s.database_url).begin() as cx:
        fila = cx.execute(select(resumenes_quechua).where(resumenes_quechua.c.id == rid)).mappings().first()
        if fila is None:
            raise HTTPException(404, f"No existe el resumen {rid}.")
        if fila["propuesto_por"] == u.id:
            raise HTTPException(403, "Quien propone el resumen no puede validarlo: debe revisarlo otra persona.")
        if fila["estado"] == "validado":
            return {"id": rid, "estado": "validado"}
        cx.execute(update(resumenes_quechua).where(resumenes_quechua.c.id == rid)
                   .values(estado="validado", validado_por=u.id, validado_en=datetime.now(timezone.utc)))
        bitacora.registrar(cx, u, "validar_resumen_quechua", "resumen_quechua", str(rid),
                           antes={"estado": "propuesto"}, despues={"estado": "validado"})
    return {"id": rid, "estado": "validado"}
