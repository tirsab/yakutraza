"""API de la Fase 3: expediente vivo, documentos, eventos, bitácora y pre-chequeo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db import get_engine
from app.expediente import bitacora as bitacora_srv
from app.expediente import documentos as docs_srv
from app.expediente import prechequeo as prechequeo_srv
from app.expediente import vivo
from app.expediente.documentos import ErrorRegistro
from app.expediente.usuarios import ErrorPermiso, Usuario, resolver, usuarios_desde
from app.vistas.sesion import alcance_eps, exige_vista
from app.vistas.privacidad import ocultar_internos
from app.persistencia import ultimo_lote
from app.plazos.repositorio import expedientes_desde_bd

router = APIRouter()


class DocumentoIn(BaseModel):
    tipo: str
    canal: str
    numero: str | None = None
    hito: str | None = None
    asunto: str | None = None
    remitente: str | None = None
    fecha_emision: date | None = None
    fecha_recepcion: date | None = None
    fecha_notificacion: date | None = None
    referencia: str | None = None
    plazo_otorgado_dh: int | None = None
    reservado: bool | None = None
    fuente: str | None = None
    cita: str | None = None
    pagina: int | None = None
    motivo: str | None = None


class EventoIn(BaseModel):
    hito: str
    tipo: str
    dias_dh: int | None = None
    nueva_fecha_limite: date | None = None
    documento_id: int | None = None
    documento_solicitud_id: int | None = None
    fecha_solicitud: date | None = None
    fuente: str | None = None
    cita: str | None = None


class CorreccionIn(BaseModel):
    motivo: str
    numero: str | None = None
    tipo: str | None = None
    hito: str | None = None
    asunto: str | None = None
    remitente: str | None = None
    fecha_emision: date | None = None
    fecha_recepcion: date | None = None
    fecha_notificacion: date | None = None
    canal: str | None = None
    plazo_otorgado_dh: int | None = None
    dias_dh: int | None = None
    nueva_fecha_limite: date | None = None
    fecha_solicitud: date | None = None
    cita: str | None = None
    pagina: int | None = None


class PrechequeoIn(BaseModel):
    cod_eps: str
    tipo_cambio: str
    anio_solicitud: int
    cod_proyecto: str | None = None
    monto_nuevo_pendiente: float | None = None
    costo_proyecto_sustituto: float | None = None
    suma_sustituciones_previas: float | None = None


def _exigir_carga(s: Settings) -> None:
    if ultimo_lote(get_engine(s.database_url)) is None:
        raise HTTPException(404, "Todavía no hay datos cargados. Ejecuta `seed`.")


def _usuario(s: Settings, x_usuario: str | None):
    if not x_usuario or not s.modo_demo:
        return None
    u = resolver(Path(s.rules_dir) / "usuarios_demo.yaml", x_usuario)
    if u is None:
        raise HTTPException(401, f"Usuario de demostración desconocido: {x_usuario}")
    return u


def _cod_eps_de(s: Settings, id_expediente: str) -> str:
    if id_expediente in vivo.casos(s):
        return "(caso real)"
    exps = expedientes_desde_bd(get_engine(s.database_url), id_expediente=id_expediente)
    if id_expediente not in exps:
        raise HTTPException(404, f"No existe el expediente {id_expediente}.")
    return exps[id_expediente].cod_eps


def _ejecutar(f):
    try:
        return f()
    except ErrorPermiso as e:
        raise HTTPException(401 if "Falta identificar" in str(e) else 403, str(e)) from e
    except ErrorRegistro as e:
        raise HTTPException(422, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/usuarios-demo", tags=["expediente vivo"])
def usuarios_demo(s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    """Usuarios FICTICIOS de demostración. Se identifican con el encabezado X-Usuario."""
    if not s.modo_demo:
        return []
    return [u.como_dict() for u in usuarios_desde(Path(s.rules_dir) / "usuarios_demo.yaml").values()]


@router.get("/expedientes", tags=["expediente vivo"])
def expedientes(tipo: str | None = None, cod_eps: str | None = None, estado: str | None = None,
                u: Usuario = Depends(exige_vista("expedientes")),
                s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    _exigir_carga(s)
    return vivo.listado(get_engine(s.database_url), s, tipo=tipo, cod_eps=alcance_eps(u, cod_eps), estado=estado)


@router.get("/expedientes/{id_expediente}", tags=["expediente vivo"])
def expediente(id_expediente: str, fecha_corte: date | None = None,
               u: Usuario = Depends(exige_vista("expedientes")),
               s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Ficha completa: línea de tiempo con evidencia, tres relojes, documentos, proyectos, pre-chequeo y bitácora.

    Una EPS solo abre sus expedientes y no ve documentos internos (informes y memorandos)."""
    _exigir_carga(s)
    if u.alcance == "propia_eps":
        alcance_eps(u, _cod_eps_de(s, id_expediente))
    f = vivo.ficha(get_engine(s.database_url), s, id_expediente, fecha_corte)
    if f is None:
        raise HTTPException(404, f"No existe el expediente {id_expediente}.")
    return ocultar_internos(f) if u.alcance == "propia_eps" else f


@router.post("/expedientes/{id_expediente}/documentos", status_code=201, tags=["expediente vivo"])
def registrar_documento(id_expediente: str, doc: DocumentoIn, x_usuario: str | None = Header(None),
                        s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Registra un documento con su canal (mesa de partes, correo, enlace externo…). Queda en la bitácora."""
    cod = _cod_eps_de(s, id_expediente)
    datos = {**doc.model_dump(exclude_none=True), "id_expediente": id_expediente}
    rid = _ejecutar(lambda: docs_srv.registrar_documento(get_engine(s.database_url), _usuario(s, x_usuario), datos, cod))
    return {"id": rid}


@router.post("/expedientes/{id_expediente}/eventos", status_code=201, tags=["expediente vivo"])
def registrar_evento(id_expediente: str, ev: EventoIn, x_usuario: str | None = Header(None),
                     s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Registra un plazo fijado por oficio o una prórroga. Solo los confirmados cambian los relojes."""
    cod = _cod_eps_de(s, id_expediente)
    datos = {**ev.model_dump(exclude_none=True), "id_expediente": id_expediente}
    rid = _ejecutar(lambda: docs_srv.registrar_evento(get_engine(s.database_url), _usuario(s, x_usuario), datos, cod))
    return {"id": rid}


@router.post("/documentos/{doc_id}/confirmar", tags=["expediente vivo"])
def confirmar_documento(doc_id: int, x_usuario: str | None = Header(None),
                        s: Settings = Depends(get_settings)) -> dict[str, Any]:
    return _ejecutar(lambda: docs_srv.confirmar_documento(get_engine(s.database_url), _usuario(s, x_usuario), doc_id))


@router.post("/documentos/{doc_id}/corregir", tags=["expediente vivo"])
def corregir_documento(doc_id: int, c: CorreccionIn, x_usuario: str | None = Header(None),
                       s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Corrige un registro propuesto (con motivo y bitácora). Sigue «propuesto» hasta que alguien lo confirme."""
    datos = c.model_dump(exclude_none=True, exclude={"motivo"})
    return _ejecutar(lambda: docs_srv.corregir_documento(get_engine(s.database_url), _usuario(s, x_usuario), doc_id,
                                                         datos, c.motivo))


@router.post("/eventos/{evento_id}/corregir", tags=["expediente vivo"])
def corregir_evento(evento_id: int, c: CorreccionIn, x_usuario: str | None = Header(None),
                    s: Settings = Depends(get_settings)) -> dict[str, Any]:
    datos = c.model_dump(exclude_none=True, exclude={"motivo"})
    return _ejecutar(lambda: docs_srv.corregir_evento(get_engine(s.database_url), _usuario(s, x_usuario), evento_id,
                                                      datos, c.motivo))


@router.post("/eventos/{evento_id}/confirmar", tags=["expediente vivo"])
def confirmar_evento(evento_id: int, x_usuario: str | None = Header(None),
                     s: Settings = Depends(get_settings)) -> dict[str, Any]:
    return _ejecutar(lambda: docs_srv.confirmar_evento(get_engine(s.database_url), _usuario(s, x_usuario), evento_id))


@router.get("/bitacora", tags=["expediente vivo"])
def leer_bitacora(id_expediente: str | None = None, u: Usuario = Depends(exige_vista("expedientes")),
                  s: Settings = Depends(get_settings)) -> list[dict[str, Any]]:
    if not u.es_sunass:
        raise HTTPException(403, "La bitácora completa es interna de Sunass.")
    return bitacora_srv.leer(get_engine(s.database_url), id_expediente=id_expediente)


@router.get("/bitacora/verificacion", tags=["expediente vivo"])
def verificar_bitacora(s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Recalcula la cadena de hashes de la bitácora."""
    return bitacora_srv.verificar(get_engine(s.database_url))


@router.get("/prechequeo/tipos", tags=["pre-chequeo"])
def tipos_prechequeo(s: Settings = Depends(get_settings)) -> dict[str, str]:
    return prechequeo_srv.catalogo_desde(Path(s.rules_dir) / "prechequeo_pi.yaml")["tipos_cambio"]


@router.post("/prechequeo/programa-inversiones", tags=["pre-chequeo"])
def prechequeo(entrada: PrechequeoIn, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Orienta si un cambio va solo con comunicación (art. 94) o con aprobación del CD (art. 93). No decide."""
    _exigir_carga(s)
    cat = prechequeo_srv.catalogo_desde(Path(s.rules_dir) / "prechequeo_pi.yaml")
    if entrada.tipo_cambio not in cat["tipos_cambio"]:
        raise HTTPException(422, f"Tipo de cambio no reconocido. Use uno de: {', '.join(cat['tipos_cambio'])}.")

    def d(v):
        return None if v is None else Decimal(str(v))

    e = prechequeo_srv.Entrada(cod_eps=entrada.cod_eps, tipo_cambio=entrada.tipo_cambio,
                               anio_solicitud=entrada.anio_solicitud, cod_proyecto=entrada.cod_proyecto,
                               monto_nuevo_pendiente=d(entrada.monto_nuevo_pendiente),
                               costo_proyecto_sustituto=d(entrada.costo_proyecto_sustituto),
                               suma_sustituciones_previas=d(entrada.suma_sustituciones_previas))
    r = prechequeo_srv.prechequear(vivo._ds03(get_engine(s.database_url)), e, cat).__dict__
    docs = cat.get("documentos_por_via", {})
    return {**r, "documentos": docs.get(r["ruta"], []), "documentos_pendientes": docs.get("pendiente"),
            "decision": "Es una orientación. La decisión final siempre es de Sunass."}
