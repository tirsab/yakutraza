"""Registro de documentos y de decisiones de plazo (plazo del oficio, prórroga).

- Lo que registra una persona de Sunass entra «confirmado».
- Lo que registra una EPS o lo que se transcribió con asistencia de IA entra
  «propuesto» y no afecta a los relojes hasta que una persona lo confirma.
- Cada alta y cada confirmación quedan en la bitácora.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection, Engine

from app.db import documentos, eventos_plazo
from app.expediente import bitacora
from app.expediente.usuarios import Usuario, exigir
from app.plazos.motor import EventoPlazo

TIPOS_DOCUMENTO = ("OF", "INF", "MEM", "RD", "RCD", "CARTA", "CORREO", "OTRO")
CANALES = ("mesa_partes", "correo", "enlace_externo", "tramite", "no_indicado", "otro")
TIPOS_EVENTO = ("plazo_oficio", "prorroga")
# Documentos internos de Sunass que la EPS no ve (Fase 5).
TIPOS_INTERNOS = ("INF", "MEM")


class ErrorRegistro(ValueError):
    pass


def tipo_desde_codigo(codigo: str | None) -> str | None:
    """«OF-2026-0018» → «OF». Los códigos de DS02 son ficticios."""
    if not codigo:
        return None
    pref = codigo.split("-")[0].upper()
    return pref if pref in TIPOS_DOCUMENTO else "OTRO"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _validar_documento(d: dict[str, Any], exigir_fecha: bool = True) -> None:
    if d.get("tipo") not in TIPOS_DOCUMENTO:
        raise ErrorRegistro(f"Tipo de documento no válido: {d.get('tipo')}. Use uno de {', '.join(TIPOS_DOCUMENTO)}.")
    if d.get("canal") not in CANALES:
        raise ErrorRegistro(f"Canal no válido: {d.get('canal')}. Use uno de {', '.join(CANALES)}.")
    if exigir_fecha and not (d.get("fecha_emision") or d.get("fecha_recepcion") or d.get("fecha_notificacion")):
        raise ErrorRegistro("Indique al menos una fecha del documento (emisión, recepción o notificación).")
    if d.get("plazo_otorgado_dh") is not None and int(d["plazo_otorgado_dh"]) < 0:
        raise ErrorRegistro("El plazo otorgado no puede ser negativo.")


def insertar_documento(cx: Connection, usuario: Usuario, d: dict[str, Any], *, origen: str, naturaleza: str,
                       estado: str, motivo: str | None = None, exigir_fecha: bool = True) -> int:
    """`exigir_fecha=False` solo para transcripciones de casos reales cuya fuente no da fecha: no se inventa."""
    _validar_documento(d, exigir_fecha)
    fila = {
        "clave": d.get("clave") or f"{d['id_expediente']}:{d['tipo']}:{d.get('numero') or _ahora().timestamp()}",
        "id_expediente": d["id_expediente"], "hito": d.get("hito"), "tipo": d["tipo"], "numero": d.get("numero"),
        "fecha_emision": d.get("fecha_emision"), "fecha_recepcion": d.get("fecha_recepcion"),
        "fecha_notificacion": d.get("fecha_notificacion"), "canal": d["canal"], "remitente": d.get("remitente"),
        "asunto": d.get("asunto"), "referencia": d.get("referencia"), "plazo_otorgado_dh": d.get("plazo_otorgado_dh"),
        "reservado": bool(d.get("reservado", d["tipo"] in TIPOS_INTERNOS)), "naturaleza": naturaleza,
        "origen": origen, "estado_registro": estado, "fuente": d.get("fuente"), "cita": d.get("cita"),
        "pagina": d.get("pagina"), "registrado_por": usuario.id, "registrado_en": _ahora(),
    }
    if estado == "confirmado":
        fila.update(confirmado_por=usuario.id, confirmado_en=_ahora())
    existente = cx.execute(select(documentos.c.id).where(documentos.c.clave == fila["clave"])).scalar()
    if existente:
        raise ErrorRegistro(f"Ya existe un documento con la clave {fila['clave']}.")
    nuevo_id = cx.execute(insert(documentos).values(**fila)).inserted_primary_key[0]
    bitacora.registrar(cx, usuario, "registrar_documento", "documento", nuevo_id, id_expediente=fila["id_expediente"],
                       despues={k: v for k, v in fila.items() if k not in ("registrado_en", "confirmado_en")},
                       motivo=motivo)
    return nuevo_id


def registrar_documento(engine: Engine, usuario: Usuario | None, d: dict[str, Any], cod_eps: str | None) -> int:
    u = exigir(usuario, "registrar_documento", cod_eps)
    estado = "confirmado" if u.es_sunass else "propuesto"
    with engine.begin() as cx:
        return insertar_documento(cx, u, d, origen="manual", naturaleza=d.get("naturaleza") or "registrado_demo",
                                  estado=estado, motivo=d.get("motivo"))


def _confirmar(engine: Engine, usuario: Usuario | None, tabla, entidad: str, rid: int) -> dict[str, Any]:
    u = exigir(usuario, "confirmar_registro")
    with engine.begin() as cx:
        fila = cx.execute(select(tabla).where(tabla.c.id == rid)).mappings().first()
        if fila is None:
            raise LookupError(f"No existe el {entidad} {rid}.")
        if fila["estado_registro"] == "confirmado":
            raise ErrorRegistro(f"El {entidad} {rid} ya estaba confirmado.")
        cambios = {"estado_registro": "confirmado", "confirmado_por": u.id, "confirmado_en": _ahora()}
        cx.execute(update(tabla).where(tabla.c.id == rid).values(**cambios))
        bitacora.registrar(cx, u, f"confirmar_{entidad}", entidad, rid, id_expediente=fila["id_expediente"],
                           antes={"estado_registro": fila["estado_registro"]},
                           despues={"estado_registro": "confirmado", "confirmado_por": u.id})
        return {**dict(fila), **cambios}


def confirmar_documento(engine: Engine, usuario: Usuario | None, doc_id: int) -> dict[str, Any]:
    return _confirmar(engine, usuario, documentos, "documento", doc_id)


def confirmar_evento(engine: Engine, usuario: Usuario | None, evento_id: int) -> dict[str, Any]:
    return _confirmar(engine, usuario, eventos_plazo, "evento", evento_id)


def insertar_evento(cx: Connection, usuario: Usuario, e: dict[str, Any], *, origen: str, naturaleza: str,
                    estado: str) -> int:
    if e.get("tipo") not in TIPOS_EVENTO:
        raise ErrorRegistro(f"Tipo de evento no válido: {e.get('tipo')}. Use {' o '.join(TIPOS_EVENTO)}.")
    if e["tipo"] == "plazo_oficio" and e.get("dias_dh") is None:
        raise ErrorRegistro("Un plazo fijado en un oficio necesita los días hábiles otorgados.")
    if e.get("dias_dh") is not None and int(e["dias_dh"]) < 0:
        raise ErrorRegistro("Los días hábiles no pueden ser negativos.")
    fila = {
        "clave": e.get("clave") or f"{e['id_expediente']}:{e['tipo']}:{e['hito']}:{_ahora().timestamp()}",
        "id_expediente": e["id_expediente"], "hito": e["hito"], "tipo": e["tipo"], "dias_dh": e.get("dias_dh"),
        "nueva_fecha_limite": e.get("nueva_fecha_limite"), "documento_id": e.get("documento_id"),
        "documento_solicitud_id": e.get("documento_solicitud_id"), "fecha_solicitud": e.get("fecha_solicitud"),
        "naturaleza": naturaleza, "origen": origen, "estado_registro": estado, "fuente": e.get("fuente"),
        "cita": e.get("cita"), "registrado_por": usuario.id, "registrado_en": _ahora(),
    }
    if estado == "confirmado":
        fila.update(confirmado_por=usuario.id, confirmado_en=_ahora())
    nuevo_id = cx.execute(insert(eventos_plazo).values(**fila)).inserted_primary_key[0]
    bitacora.registrar(cx, usuario, "registrar_evento", "evento", nuevo_id, id_expediente=fila["id_expediente"],
                       despues={k: v for k, v in fila.items() if k not in ("registrado_en", "confirmado_en")})
    return nuevo_id


def registrar_evento(engine: Engine, usuario: Usuario | None, e: dict[str, Any], cod_eps: str | None) -> int:
    u = exigir(usuario, "registrar_evento", cod_eps)
    with engine.begin() as cx:
        return insertar_evento(cx, u, e, origen="manual", naturaleza=e.get("naturaleza") or "registrado_demo",
                               estado="confirmado" if u.es_sunass else "propuesto")


def listar(engine: Engine, tabla, id_expediente: str) -> list[dict[str, Any]]:
    with engine.connect() as cx:
        return [dict(r) for r in cx.execute(select(tabla).where(tabla.c.id_expediente == id_expediente)
                                            .order_by(tabla.c.id)).mappings()]


def eventos_para_motor(engine: Engine, id_expediente: str) -> list[EventoPlazo]:
    """Solo los eventos confirmados por una persona afectan a los relojes."""
    docs = {d["id"]: d for d in listar(engine, documentos, id_expediente)}
    res = []
    for e in listar(engine, eventos_plazo, id_expediente):
        if e["estado_registro"] != "confirmado":
            continue
        doc = docs.get(e["documento_id"]) or {}
        sol = docs.get(e["documento_solicitud_id"]) or {}
        fecha_doc = doc.get("fecha_notificacion") or doc.get("fecha_emision") or doc.get("fecha_recepcion")
        res.append(EventoPlazo(
            expediente=id_expediente, hito=e["hito"], tipo=e["tipo"], documento=doc.get("numero") or f"evento {e['id']}",
            fecha_documento=fecha_doc or date.min, dias_adicionales_dh=e["dias_dh"],
            nueva_fecha_limite=e["nueva_fecha_limite"], documento_solicitud=sol.get("numero"),
            fecha_solicitud=e["fecha_solicitud"], naturaleza=e["naturaleza"], fuente=e.get("fuente") or "",
        ))
    return res
