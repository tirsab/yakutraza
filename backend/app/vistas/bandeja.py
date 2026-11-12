"""Bandeja «mi siguiente acción» (Fase 5).

Cada fila responde tres preguntas sin abrir el expediente:
1. ¿Qué requiere acción? El reloj más urgente y el siguiente paso.
2. ¿Qué evidencia falta? Hitos «declarados, no verificados» y registros propuestos sin confirmar.
3. ¿Por qué importa? Días vencidos o restantes, monto, proyecto, meta y población (estimada).

Orden: por plazo restante (vencidos primero), nunca por tamaño de la EPS.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.calidad.reglas._util import soles
from app.db import TABLAS_DATASETS, documentos, eventos_plazo
from app.expediente.casos_reales import pendientes
from app.expediente.documentos import listar
from app.expediente.vivo import DECLARADO, casos, pasaporte
from app.vistas.etiquetas import etiqueta
from app.vistas.tablero import ORDEN, Contexto, Fila, especialista_de

SUNASS_TECNICO = ("Equipo SRT", "SRT")
EP = ("EP", "EP e interesados")


def _ds02(engine: Engine, ids: list[str]) -> dict[str, dict[str, Any]]:
    tp = TABLAS_DATASETS["ds02_procedimientos"]
    with engine.connect() as cx:
        return {r["id_expediente"]: dict(r) for r in cx.execute(select(tp).where(tp.c.id_expediente.in_(ids))).mappings()}


def _proyecto(engine: Engine, cod: str | None) -> dict[str, Any] | None:
    if not cod:
        return None
    t = TABLAS_DATASETS["ds03_programa_inversiones"]
    with engine.connect() as cx:
        filas = [dict(r) for r in cx.execute(select(t).where(t.c.cod_proyecto == cod)).mappings()]
    if not filas:
        return None
    f = filas[0]
    return {"cod_proyecto": cod, "nombre": f["nombre_proyecto"], "localidad": f["localidad"],
            "meta_asociada": f["meta_asociada"], "poblacion_beneficiaria": f["poblacion_beneficiaria"],
            "naturaleza_poblacion": "estimado",
            "monto_programado_vigente": float(sum((r["monto_programado_vigente"] or 0) for r in filas))}


def siguiente_paso(f: Fila, cat: dict[str, Any]) -> str:
    a, h = f.alerta, f.hito
    if a is not None and a.estado == "no_calculable":
        return "Completar el dato que falta para poder calcular el plazo."
    if a is not None and a.reloj == "oficio":
        return "Hacer seguimiento a la respuesta de la EP al oficio."
    if h is None:
        return "Revisar el expediente: no hay un hito en curso a la fecha de corte."
    nombre = etiqueta(cat, "hito", h.hito)
    if h.responsable in SUNASS_TECNICO:
        return f"Te toca: {nombre}."
    if h.responsable in EP:
        return f"Esperar a la EP: {nombre}."
    return f"Hacer seguimiento: está en {etiqueta(cat, 'responsable', h.responsable)} ({nombre})."


def evidencia_faltante(f: Fila, docs: list[dict[str, Any]], corte, cat: dict[str, Any]) -> list[dict[str, Any]]:
    por_hito: dict[str, list[dict[str, Any]]] = {}
    for d in docs:
        por_hito.setdefault(d["hito"] or "", []).append(d)
    faltan = []
    for h in f.exp.hitos:
        if h.fecha_inicio is None or h.fecha_inicio > corte:
            continue
        p = pasaporte(h, por_hito.get(h.hito, []))
        if p["estado"] == DECLARADO:
            faltan.append({"tipo": "sin_documento", "hito": h.hito, "responsable": h.responsable,
                           "texto": f"{etiqueta(cat, 'hito', h.hito)}: declarado, no verificado (sin documento).",
                           "fila_ds02": h.fila})
    for d in docs:
        if d["estado_registro"] != "confirmado":
            faltan.append({"tipo": "por_confirmar", "hito": d["hito"], "documento_id": d["id"],
                           "texto": f"{d['numero'] or 'Documento'}: registro propuesto, falta confirmar."})
    return faltan


def por_que_importa(f: Fila, p: dict[str, Any] | None, proyecto: dict[str, Any] | None) -> list[str]:
    razones = []
    a = f.alerta
    if a is not None and a.dias_restantes is not None:
        if a.dias_restantes < 0:
            razones.append(f"Vencido hace {-a.dias_restantes} días hábiles ({a.titulo.lower()}).")
        else:
            razones.append(f"Quedan {a.dias_restantes} días hábiles ({a.titulo.lower()}).")
    if a is not None and a.reloj == "normativo" and a.estado == "vencido":
        razones.append("Superó el plazo máximo del procedimiento: el RGT lo sujeta a silencio administrativo "
                       "positivo (cómo informarlo está por validar, DRE-15).")
    if p and p.get("monto_solicitado"):
        razones.append(f"Monto solicitado: {_soles(p['monto_solicitado'])}.")
    if proyecto:
        texto = f"Proyecto {proyecto['cod_proyecto']} ({proyecto['nombre']}, {proyecto['localidad']})"
        if proyecto.get("poblacion_beneficiaria"):
            texto += f": {int(proyecto['poblacion_beneficiaria']):,} personas beneficiarias (estimado)".replace(",", " ")
        if proyecto.get("meta_asociada"):
            texto += f"; impulsa la meta de gestión {proyecto['meta_asociada']}"
        razones.append(texto + ".")
    return razones


def _soles(v) -> str:
    return soles(Decimal(str(v)))


def items(ctx: Contexto, filas: list[Fila], cat: dict[str, Any]) -> list[dict[str, Any]]:
    p_ds02 = _ds02(ctx.engine, [f.exp.id for f in filas])
    res = []
    for f in filas:
        p = p_ds02.get(f.exp.id)
        proyecto = _proyecto(ctx.engine, p.get("cod_proyecto") if p else None)
        docs = listar(ctx.engine, documentos, f.exp.id)
        res.append({**f.como_dict(), "siguiente_paso": siguiente_paso(f, cat),
                    "evidencia_faltante": evidencia_faltante(f, docs, ctx.corte, cat),
                    "por_que_importa": por_que_importa(f, p, proyecto), "proyecto": proyecto,
                    "monto_solicitado": float(p["monto_solicitado"]) if p and p.get("monto_solicitado") else None,
                    "fuente": f"DS02 fila {f.exp.fila} (sintético); relojes del motor de plazos"})
    return res


def items_casos_reales(ctx: Contexto, especialistas: list[str]) -> list[dict[str, Any]]:
    """Casos reales con transcripciones sin confirmar: sin confirmación, sus relojes no se calculan."""
    res = []
    for c in casos(ctx.s).values():
        faltan = pendientes(ctx.engine, c)
        if not faltan:
            continue
        e = c.datos["expediente"]
        regs = {r["clave"]: r for t in (documentos, eventos_plazo) for r in listar(ctx.engine, t, e["id"])}
        res.append({
            "id_expediente": e["id"], "cod_eps": None, "empresa": e.get("empresa"), "tipo_procedimiento": e["procedimiento"],
            "especialista": especialista_de(e["id"], especialistas), "estado": "no_calculable",
            "hito_al_corte": None, "responsable_al_corte": None, "desde": None, "fecha_inicio": e.get("fecha_inicio"),
            "alerta": {"reloj": "normativo", "estado": "no_calculable", "titulo": "Relojes en espera de confirmación",
                       "mensaje": f"Falta confirmar {len(faltan)} registros transcritos con asistencia de IA.",
                       "dias_restantes": None, "fecha_limite": None, "fuente": c.datos["fuente_principal"]},
            "relojes": {"normativo": "no_calculable", "interno": None, "oficio": None},
            "siguiente_paso": "Confirmar la transcripción de los documentos del caso real.",
            "evidencia_faltante": [{"tipo": "por_confirmar", "hito": regs.get(k, {}).get("hito"),
                                    "documento_id": regs.get(k, {}).get("id"),
                                    "texto": f"{regs.get(k, {}).get('numero') or k}: propuesto, falta confirmar."}
                                   for k in faltan],
            "por_que_importa": ["Caso real de referencia: sin confirmación de una persona, sus relojes no se calculan."],
            "proyecto": None, "monto_solicitado": None, "naturaleza": "real", "fila_ds02": None,
            "fuente": c.datos["fuente_principal"]})
    return res


def ordenar(xs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def clave(x):
        a = x.get("alerta") or {}
        d = a.get("dias_restantes")
        return (ORDEN.get(x["estado"], 9), d if d is not None else 10**6, x["id_expediente"])
    return sorted(xs, key=clave)
