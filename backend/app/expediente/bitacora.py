"""Bitácora de cambios: solo se agrega y cada entrada encadena el hash de la anterior.

El trigger de la migración 0002 impide UPDATE y DELETE en la base. El hash
encadenado permite verificar que nadie alteró entradas por fuera de la API.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.engine import Connection, Engine

from app.db import bitacora
from app.expediente.usuarios import Usuario

HASH_INICIAL = "0" * 64
CAMPOS = ("cuando", "usuario", "rol", "accion", "entidad", "entidad_id", "id_expediente", "antes", "despues", "motivo")


def _normalizar(v: Any) -> Any:
    return json.loads(json.dumps(v, default=str, sort_keys=True)) if v is not None else None


def _cuando(v) -> str:
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:  # SQLite devuelve fechas sin zona; se guardan en UTC
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc).isoformat(timespec="microseconds")


def calcular_hash(fila: dict[str, Any], hash_anterior: str) -> str:
    datos = {c: _normalizar(fila.get(c)) for c in CAMPOS}
    datos["cuando"] = _cuando(fila["cuando"])
    datos["hash_anterior"] = hash_anterior
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def registrar(cx: Connection, usuario: Usuario, accion: str, entidad: str, entidad_id: str, *,
              id_expediente: str | None = None, antes: Any = None, despues: Any = None,
              motivo: str | None = None) -> dict[str, Any]:
    previo = cx.execute(select(bitacora.c.hash).order_by(bitacora.c.id.desc()).limit(1)).scalar()
    fila = {
        "cuando": datetime.now(timezone.utc), "usuario": usuario.id, "rol": usuario.rol, "accion": accion,
        "entidad": entidad, "entidad_id": str(entidad_id), "id_expediente": id_expediente,
        "antes": _normalizar(antes), "despues": _normalizar(despues), "motivo": motivo,
    }
    anterior = previo or HASH_INICIAL
    fila["hash_anterior"] = anterior
    fila["hash"] = calcular_hash(fila, anterior)
    cx.execute(insert(bitacora).values(**fila))
    return fila


def leer(engine: Engine, id_expediente: str | None = None, entidad_id: str | None = None) -> list[dict[str, Any]]:
    q = select(bitacora).order_by(bitacora.c.id)
    if id_expediente:
        q = q.where(bitacora.c.id_expediente == id_expediente)
    if entidad_id:
        q = q.where(bitacora.c.entidad_id == entidad_id)
    with engine.connect() as cx:
        return [dict(r) for r in cx.execute(q).mappings()]


def verificar(engine: Engine) -> dict[str, Any]:
    """Recalcula la cadena completa. Devuelve si está íntegra y, si no, la primera entrada alterada."""
    anterior = HASH_INICIAL
    with engine.connect() as cx:
        filas = [dict(r) for r in cx.execute(select(bitacora).order_by(bitacora.c.id)).mappings()]
    for f in filas:
        if f["hash_anterior"] != anterior or calcular_hash(f, anterior) != f["hash"]:
            return {"integra": False, "entradas": len(filas), "primera_alterada": f["id"]}
        anterior = f["hash"]
    return {"integra": True, "entradas": len(filas), "primera_alterada": None}
