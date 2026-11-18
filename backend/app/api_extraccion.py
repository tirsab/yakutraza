"""API de la Fase 6: extracción asistida con IA. Lo extraído es una PROPUESTA: solo entra al expediente cuando
una persona lo confirma (o lo corrige y lo confirma), y queda en la bitácora."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.config import Settings, get_settings
from app.db import documentos, get_engine
from app.expediente.documentos import ErrorRegistro, insertar_documento, insertar_evento
from app.expediente.usuarios import ErrorPermiso, Usuario, exigir
from app.extraccion import servicio as sv
from app.extraccion.extraer import leer_fecha as _fecha
from app.extraccion.proveedores import ErrorProveedor
from app.vistas.sesion import exige_vista

router = APIRouter(prefix="/extraccion", tags=["extracción con IA"])


def _sunass(u: Usuario) -> Usuario:
    if not u.es_sunass:
        raise HTTPException(403, "La extracción asistida es solo para el personal de Sunass.")
    return u


@router.get("/estado")
def estado(u: Usuario = Depends(exige_vista("expedientes")), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Proveedor configurado y si responde. No envía ningún texto."""
    _sunass(u)
    p = sv.proveedor_de(s)
    disponible, detalle = False, "Extracción desactivada (EXTRACCION_PROVEEDOR=ninguno)."
    if p is not None and p.nombre == "ollama":
        try:
            r = httpx.get(f"{s.ollama_url.rstrip('/')}/api/tags", timeout=3)
            modelos = [m.get("name") for m in r.json().get("models", [])]
            disponible = any(m == s.ollama_modelo or m.startswith(f"{s.ollama_modelo}:") for m in modelos)
            detalle = ("Ollama listo." if disponible else
                       f"Ollama responde, pero falta el modelo. Ejecute: ollama pull {s.ollama_modelo}")
        except (httpx.HTTPError, ValueError):
            detalle = f"Ollama no responde en {s.ollama_url}. ¿Está instalado y abierto?"
    elif p is not None:
        disponible, detalle = True, "API de Anthropic configurada (solo recibe texto anonimizado)."
    return {"proveedor": s.extraccion_proveedor, "modelo": p.modelo if p else None, "disponible": disponible,
            "detalle": detalle, "parte_privada": s.casos_reales_privados,
            "lista_privada": bool(sv.ruta_lista_privada(s) and sv.ruta_lista_privada(s).exists())}


@router.get("/documentos")
def documentos_reales(id_expediente: str | None = None, u: Usuario = Depends(exige_vista("expedientes")),
                      s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    """Documentos de los casos reales, por alias (nunca por nombre de archivo)."""
    _sunass(u)
    return [{**d.publico(), "procesado": sv.ultimo(s, d.alias) is not None} for d in sv.indice(s)
            if not id_expediente or d.id_expediente == id_expediente]


@router.get("/documentos/{alias}")
def ver(alias: str, u: Usuario = Depends(exige_vista("expedientes")), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    _sunass(u)
    if not any(d.alias == alias for d in sv.indice(s)):
        raise HTTPException(404, f"No existe el documento {alias} (o la parte privada no está habilitada).")
    r = sv.ultimo(s, alias)
    if r is None:
        raise HTTPException(404, f"{alias} todavía no se leyó con IA.")
    return r


@router.post("/documentos/{alias}")
def leer(alias: str, u: Usuario = Depends(exige_vista("expedientes")), s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Lee el documento con el modelo configurado. Anonimiza antes; valida cada cita; no registra nada."""
    _sunass(u)
    try:
        return sv.extraer(s, alias)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except sv.ErrorPrivacidad as e:
        raise HTTPException(422, str(e)) from e
    except ErrorProveedor as e:
        raise HTTPException(503, str(e)) from e


class PlazoIn(BaseModel):
    dias_habiles: int
    tipo: str | None = None


class ConfirmacionIn(BaseModel):
    hito: str
    numero_documento: str | None = None
    fecha: str | None = None
    remitente: str | None = None
    plazo: PlazoIn | None = None
    motivo_correccion: str | None = None


def _tipo(numero: str | None) -> str:
    n = (numero or "").lower()
    for pref, tipo in (("oficio", "OF"), ("informe", "INF"), ("memor", "MEM"), ("resoluci", "RCD"), ("rcd", "RCD"),
                       ("carta", "CARTA")):
        if n.startswith(pref):
            return tipo
    return "OTRO"


@router.post("/documentos/{alias}/confirmar", status_code=201)
def confirmar(alias: str, c: ConfirmacionIn, u: Usuario = Depends(exige_vista("expedientes")),
              s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Una persona confirma lo propuesto (o lo corrige). Recién entonces entra al expediente, con su bitácora."""
    _sunass(u)
    try:
        exigir(u, "confirmar_registro")
    except ErrorPermiso as e:
        raise HTTPException(403, str(e)) from e
    r = sv.ultimo(s, alias)
    if r is None:
        raise HTTPException(404, f"{alias} todavía no se leyó con IA.")
    campos = r["campos"]
    propuesto = {"numero_documento": (campos.get("numero_documento") or {}).get("valor"),
                 "fecha": (campos.get("fecha") or {}).get("valor"),
                 "remitente": (campos.get("remitente") or {}).get("valor"),
                 "plazo": (campos.get("plazo") or {}).get("dias_habiles")}
    final = {"numero_documento": c.numero_documento, "fecha": c.fecha, "remitente": c.remitente,
             "plazo": c.plazo.dias_habiles if c.plazo else None}
    corregidos = [k for k in final if final[k] != propuesto[k]]
    if corregidos and (not c.motivo_correccion or len(c.motivo_correccion.strip()) < 5):
        raise HTTPException(422, f"Cambió {', '.join(corregidos)} respecto de lo propuesto: indique el motivo de la corrección.")
    plazo_cita = campos.get("plazo") or {}
    fuente = (f"Extracción asistida con IA ({r['proveedor']}, {r['modelo']}) del documento {alias}"
              f"{', pág. ' + str(plazo_cita.get('pagina')) if plazo_cita.get('pagina') else ''}; confirmado por {u.id}"
              + (f"; corregido: {', '.join(corregidos)}" if corregidos else ""))
    clave = f"{r['id_expediente']}:IA:{alias}"
    eng = get_engine(s.database_url)
    with eng.begin() as cx:
        if cx.execute(select(documentos.c.id).where(documentos.c.clave == clave)).first():
            raise HTTPException(409, f"Lo extraído de {alias} ya se confirmó.")
        try:
            doc_id = insertar_documento(cx, u, {
                "clave": clave, "id_expediente": r["id_expediente"], "tipo": _tipo(c.numero_documento), "canal": "no_indicado",
                "numero": c.numero_documento, "hito": c.hito, "remitente": c.remitente,
                "fecha_emision": _fecha(c.fecha), "plazo_otorgado_dh": c.plazo.dias_habiles if c.plazo else None,
                "fuente": fuente, "cita": plazo_cita.get("cita") or (campos.get("numero_documento") or {}).get("cita"),
                "pagina": plazo_cita.get("pagina")},
                origen="extraido_ia", naturaleza="real", estado="confirmado",
                motivo=c.motivo_correccion if corregidos else "Confirmado sin cambios", exigir_fecha=False)
            evento_id = None
            if c.plazo and (c.plazo.tipo or "").lower() in ("prorroga", "prórroga", "otorgado"):
                evento_id = insertar_evento(cx, u, {
                    "clave": f"{clave}:PLAZO", "id_expediente": r["id_expediente"], "hito": c.hito,
                    "tipo": "prorroga" if c.plazo.tipo.lower().startswith("pr") else "plazo_oficio",
                    "dias_dh": c.plazo.dias_habiles, "documento_id": doc_id, "fuente": fuente, "cita": plazo_cita.get("cita")},
                    origen="extraido_ia", naturaleza="real", estado="confirmado")
        except ErrorRegistro as e:
            raise HTTPException(422, str(e)) from e
    return {"documento_id": doc_id, "evento_id": evento_id, "corregidos": corregidos}
