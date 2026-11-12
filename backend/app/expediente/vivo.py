"""Ficha del expediente vivo: línea de tiempo, pasaporte de evidencia, relojes,
documentos, proyectos afectados, pre-chequeo y bitácora.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.config import Settings, dir_privado
from app.db import TABLAS_DATASETS, documentos, eventos_plazo
import yaml

from app.dinero import ruta
from app.dinero.ruta import a_json as _json
from app.dinero.datos import tablas
from app.expediente import bitacora
from app.expediente.casos_reales import cargar_casos, expediente_de, pendientes
from app.expediente.documentos import eventos_para_motor, listar, tipo_desde_codigo
from app.expediente.prechequeo import Entrada, catalogo_desde, prechequear
from app.plazos.calendario import calendario_desde
from app.plazos.catalogo import catalogo_desde as catalogo_plazos
from app.plazos.motor import Expediente, MotorPlazos
from app.plazos.repositorio import expedientes_desde_bd

DECLARADO = "declarado, no verificado"
CODIGO_DS02 = "código en DS02, sin archivo"
REGISTRADO = "documento registrado"
PROPUESTO = "registro propuesto, falta confirmar"


def _motor(s: Settings) -> MotorPlazos:
    r = Path(s.rules_dir)
    return MotorPlazos(calendario_desde(r / "feriados.yaml"), catalogo_plazos(r / "plazos.yaml"))


def casos(s: Settings):
    return cargar_casos(Path(s.casos_reales_dir), dir_privado(s))


def _estado_hito(h, corte: date) -> str:
    if h.fecha_inicio is None:
        return "sin fecha de inicio"
    if h.fecha_fin is not None and h.fecha_fin < h.fecha_inicio:
        return "fecha inconsistente"
    if h.fecha_inicio > corte:
        return "no iniciado"
    if h.fecha_fin is None or h.fecha_fin > corte:
        return "en curso"
    return "concluido"


def pasaporte(h, docs_hito: list[dict[str, Any]]) -> dict[str, Any]:
    """Evidencia de un hito: documentos registrados, código de DS02 o «declarado, no verificado»."""
    confirmados = [d for d in docs_hito if d["estado_registro"] == "confirmado"]
    if confirmados:
        estado = REGISTRADO
    elif docs_hito:
        estado = PROPUESTO
    elif h.documento:
        estado = CODIGO_DS02
    else:
        estado = DECLARADO
    principal = (confirmados or docs_hito or [None])[0]
    return {"estado": estado,
            "referencia": principal["numero"] if principal else h.documento,
            "tipo": principal["tipo"] if principal else tipo_desde_codigo(h.documento),
            "codigo_ds02": h.documento if principal is None else None,
            "documentos": [d["id"] for d in docs_hito]}


def _proyectos(engine: Engine, cod_proyecto: str | None) -> list[dict[str, Any]]:
    if not cod_proyecto:
        return []
    t = TABLAS_DATASETS["ds03_programa_inversiones"]
    with engine.connect() as cx:
        filas = [dict(r) for r in cx.execute(select(t).where(t.c.cod_proyecto == cod_proyecto).order_by(t.c.anio)).mappings()]
    if not filas:
        return []
    f0 = filas[0]
    return [{
        "cod_proyecto": cod_proyecto, "nombre": f0["nombre_proyecto"], "cui": f0["cui"], "localidad": f0["localidad"],
        "componente": f0["componente"], "meta_asociada": f0["meta_asociada"],
        "poblacion_beneficiaria": f0["poblacion_beneficiaria"], "naturaleza_poblacion": "estimado",
        "anios": [{"anio": r["anio"], "original": r["monto_programado_original"], "vigente": r["monto_programado_vigente"],
                   "id_expediente_modificacion": r["id_expediente_modificacion"], "fila": r["fila_origen"]}
                  for r in filas],
        "fuente": "DS03 programa de inversiones (sintético)",
    }]


def _ds03(engine: Engine) -> pd.DataFrame:
    t = TABLAS_DATASETS["ds03_programa_inversiones"]
    with engine.connect() as cx:
        df = pd.DataFrame(cx.execute(select(t)).mappings().all())
    if not df.empty:
        df = df.rename(columns={"fila_origen": "_fila"})
        df = df.astype(object).where(df.notna(), None)
    return df


def prechequeo_de_ds02(engine: Engine, s: Settings, exp: Expediente, monto, cod_proyecto) -> dict[str, Any] | None:
    if exp.tipo != "cambio_programa_inversiones" or exp.fecha_inicio is None:
        return None
    entrada = Entrada(cod_eps=exp.cod_eps, tipo_cambio="incremento_monto", anio_solicitud=exp.fecha_inicio.year,
                      cod_proyecto=cod_proyecto, monto_nuevo_pendiente=monto, id_expediente=exp.id)
    r = prechequear(_ds03(engine), entrada, catalogo_desde(Path(s.rules_dir) / "prechequeo_pi.yaml"))
    r.supuestos.insert(0, "DS02 no registra la causal del cambio: se evalúa como incremento de monto (supuesto). "
                          "Es un contraste informativo; no recalifica la vía que siguió el expediente.")
    return r.__dict__


def ficha(engine: Engine, s: Settings, id_expediente: str, corte: date | None = None) -> dict[str, Any] | None:
    corte = corte or s.fecha_corte
    motor = _motor(s)
    caso = casos(s).get(id_expediente)
    docs = listar(engine, documentos, id_expediente)
    evs = listar(engine, eventos_plazo, id_expediente)
    if caso is not None:
        exp = expediente_de(caso)
        e = caso.datos["expediente"]
        meta = {"id_expediente": exp.id, "cod_eps": None, "empresa": e["empresa"], "tipo_procedimiento": exp.tipo,
                "naturaleza": "real", "estado": e.get("estado"), "resultado": e.get("resultado"),
                "numero_expediente_sunass": e.get("numero_expediente_sunass"), "fecha_inicio": exp.fecha_inicio,
                "fecha_conclusion": exp.fecha_conclusion, "plazo_maximo_dh": exp.plazo_maximo_dh,
                "fuente": caso.datos["fuente_principal"], "con_detalle_privado": caso.con_detalle_privado,
                "campos_privados": caso.campos_privados, "montos": caso.datos.get("montos", []),
                "base_normativa": caso.datos.get("base_normativa"),
                "aviso": "Caso real transcrito con asistencia de IA: cada documento debe confirmarlo una persona."}
        faltan = pendientes(engine, caso)
        if faltan:
            relojes = [{
                "expediente": exp.id, "cod_eps": None, "reloj": "normativo", "estado": "no_calculable",
                "en_curso": True, "titulo": "Relojes en espera de confirmación",
                "mensaje": "No puedo calcular todavía: falta que una persona confirme " + ", ".join(faltan) + ".",
                "regla_id": None, "fuente": caso.datos["fuente_principal"], "estado_validacion": "por validar",
                "respaldo": None, "hito": None, "etapa": None, "fecha_inicio": None, "fecha_limite": None,
                "plazo_dh": None, "dias_transcurridos": None, "dias_restantes": None, "documento_inicio": None,
                "documento_estado": None, "discrepancia": None, "detalle": {"pendientes": faltan}}]
        else:
            relojes = [a.como_dict() for a in motor.relojes(exp, corte, eventos_para_motor(engine, exp.id))]
        proyectos, pre = [], None
    else:
        exps = expedientes_desde_bd(engine, id_expediente=id_expediente)
        if id_expediente not in exps:
            return None
        exp = exps[id_expediente]
        tp = TABLAS_DATASETS["ds02_procedimientos"]
        with engine.connect() as cx:
            p = dict(cx.execute(select(tp).where(tp.c.id_expediente == id_expediente)).mappings().first())
        meta = {"id_expediente": exp.id, "cod_eps": exp.cod_eps, "empresa": None, "tipo_procedimiento": exp.tipo,
                "naturaleza": "sintético", "estado": p["estado"], "resultado": p["resultado"],
                "base_normativa": p["base_normativa"], "fecha_inicio": exp.fecha_inicio,
                "fecha_conclusion": exp.fecha_conclusion, "fecha_limite_ds02": p["fecha_limite"],
                "plazo_maximo_dh": exp.plazo_maximo_dh, "hito_actual": p["hito_actual"],
                "responsable_actual": p["responsable_actual"], "monto_solicitado": p["monto_solicitado"],
                "monto_aprobado": p["monto_aprobado"], "documento_final": p["documento_final"],
                "fila_ds02": p["fila_origen"], "fuente": f"DS02 ds02_procedimientos, fila {p['fila_origen']} (sintético)"}
        relojes = [a.como_dict() for a in motor.relojes(exp, corte, eventos_para_motor(engine, exp.id))]
        proyectos = _proyectos(engine, p["cod_proyecto"])
        pre = prechequeo_de_ds02(engine, s, exp, p["monto_solicitado"], p["cod_proyecto"])

    por_hito: dict[str, list[dict[str, Any]]] = {}
    for d in docs:
        por_hito.setdefault(d["hito"] or "", []).append(d)
    linea = []
    for h in exp.hitos:
        linea.append({
            "nro": h.nro, "hito": h.hito, "descripcion": h.descripcion, "etapa": h.etapa, "responsable": h.responsable,
            "fecha_inicio": h.fecha_inicio, "fecha_fin": h.fecha_fin, "plazo_referencial_dh": h.plazo_referencial_dh,
            "cuenta_plazo": h.cuenta_plazo, "estado": _estado_hito(h, corte), "fila_ds02": h.fila,
            "evidencia": pasaporte(h, por_hito.get(h.hito, [])),
            "alertas": [a for a in relojes if a.get("hito") == h.hito],
        })
    return {"expediente": meta, "fecha_corte": corte, "linea_de_tiempo": linea, "relojes": relojes,
            "documentos": docs, "eventos": evs, "proyectos": proyectos, "prechequeo": pre,
            "ruta_dinero": _json(_ruta_dinero(s, caso, exp, proyectos)),
            "bitacora": bitacora.leer(engine, id_expediente=id_expediente)}


def _ruta_dinero(s: Settings, caso, exp: Expediente, proyectos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Ruta del dinero del expediente (Fase 4): uso del fondo o proyectos afectados."""
    cfg = yaml.safe_load((Path(s.rules_dir) / "ruta_dinero.yaml").read_text(encoding="utf-8"))
    if caso is not None:
        return ruta.ruta_caso_real(caso)
    t = tablas(s.database_url)
    if exp.tipo == "uso_excepcional_fondo":
        return ruta.ruta_expediente_uso(t, exp.id, cfg["textos"])
    if proyectos:
        return {"proyectos": [ruta.detalle_proyecto(t, cfg["parametros"], cfg["textos"], p["cod_proyecto"])
                              for p in proyectos]}
    return None


def listado(engine: Engine, s: Settings, tipo: str | None = None, cod_eps: str | None = None,
            estado: str | None = None) -> list[dict[str, Any]]:
    tp = TABLAS_DATASETS["ds02_procedimientos"]
    q = select(tp.c.id_expediente, tp.c.cod_eps, tp.c.tipo_procedimiento, tp.c.estado, tp.c.fecha_inicio,
               tp.c.hito_actual, tp.c.responsable_actual, tp.c.fecha_limite)
    if tipo:
        q = q.where(tp.c.tipo_procedimiento == tipo)
    if cod_eps:
        q = q.where(tp.c.cod_eps == cod_eps)
    if estado:
        q = q.where(tp.c.estado == estado)
    with engine.connect() as cx:
        res = [{**dict(r), "naturaleza": "sintético"} for r in cx.execute(q.order_by(tp.c.id_expediente)).mappings()]
    if not cod_eps:
        for c in casos(s).values():
            e = c.datos["expediente"]
            if (tipo is None or tipo == e["procedimiento"]) and (estado is None or estado == e.get("estado")):
                res.insert(0, {"id_expediente": e["id"], "cod_eps": None, "tipo_procedimiento": e["procedimiento"],
                               "estado": e.get("estado"), "fecha_inicio": e.get("fecha_inicio"), "hito_actual": None,
                               "responsable_actual": None, "fecha_limite": None, "naturaleza": "real",
                               "empresa": e["empresa"]})
    return res
