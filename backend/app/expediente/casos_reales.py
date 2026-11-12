"""Casos reales de referencia.

- Parte pública (versionada): casos_reales/<caso>.yaml. Solo lo que cita una
  resolución publicada.
- Parte privada (no versionada): <dir privado>/<caso>_detalle.yaml. Detalles de
  los oficios intermedios; completa registros públicos, nunca crea nuevos.

Todo entra «propuesto (transcrito con asistencia de IA)» y solo afecta a los
relojes cuando una persona confirma cada documento y cada evento.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select, update
from sqlalchemy.engine import Connection, Engine

from app.db import documentos, eventos_plazo
from app.expediente import bitacora
from app.expediente.documentos import insertar_documento, insertar_evento
from app.expediente.usuarios import Usuario
from app.plazos.motor import Expediente, Hito

# Usuario técnico que carga las transcripciones (no es una persona).
SISTEMA = Usuario(id="sistema-carga", nombre="Carga automática de casos reales", rol="sistema", unidad="YakuTraza",
                  permisos=("registrar_documento", "registrar_evento"))

CAMPOS_DOC = ("tipo", "numero", "hito", "asunto", "remitente", "fecha_emision", "fecha_recepcion",
              "fecha_notificacion", "canal", "plazo_otorgado_dh", "referencia")


@dataclass
class CasoReal:
    caso: str
    datos: dict[str, Any]
    archivo_publico: str
    archivo_privado: str | None = None
    campos_privados: list[str] = field(default_factory=list)

    @property
    def id_expediente(self) -> str:
        return self.datos["expediente"]["id"]

    @property
    def con_detalle_privado(self) -> bool:
        return self.archivo_privado is not None


def _combinar(base: list[dict], extra: list[dict] | None, llave: str, marcas: list[str], prefijo: str) -> None:
    por_llave = {x[llave]: x for x in base}
    for e in extra or []:
        destino = por_llave.get(e[llave])
        if destino is None:
            continue  # la parte privada solo completa registros públicos
        for k, v in e.items():
            if k != llave:
                destino[k] = v
                marcas.append(f"{prefijo} {e[llave]}: {k}")


def cargar_casos(dir_publico: Path, dir_privado: Path) -> dict[str, CasoReal]:
    casos: dict[str, CasoReal] = {}
    for ruta in sorted(Path(dir_publico).glob("*.yaml")):
        datos = copy.deepcopy(yaml.safe_load(ruta.read_text(encoding="utf-8")))
        privado = Path(dir_privado) / f"{ruta.stem}_detalle.yaml"
        caso = CasoReal(datos["caso"], datos, ruta.name)
        if privado.exists():
            extra = yaml.safe_load(privado.read_text(encoding="utf-8")) or {}
            _combinar(datos["documentos"], extra.get("documentos"), "clave", caso.campos_privados, "documento")
            _combinar(datos.setdefault("eventos", []), extra.get("eventos"), "clave", caso.campos_privados, "evento")
            _combinar(datos["hitos"], extra.get("hitos"), "nro", caso.campos_privados, "hito")
            caso.archivo_privado = privado.name
        casos[caso.id_expediente] = caso
    return casos


def _fuente(caso: CasoReal, x: dict) -> str:
    texto = f"{caso.datos['fuente_principal']}, pág. {x.get('pagina')}"
    if x.get("fuente_detalle"):
        texto += f"; detalle: {x['fuente_detalle']} (parte privada, no versionada)"
    return texto


def _fila_documento(caso: CasoReal, d: dict) -> dict[str, Any]:
    return {"clave": d["clave"], "id_expediente": caso.id_expediente, **{k: d.get(k) for k in CAMPOS_DOC},
            "fuente": _fuente(caso, d), "cita": d.get("cita_detalle") or d.get("cita"), "pagina": d.get("pagina")}


def _fila_evento(caso: CasoReal, e: dict, ids_doc: dict[str, int]) -> dict[str, Any]:
    return {"clave": e["clave"], "id_expediente": caso.id_expediente, "hito": e["hito"], "tipo": e["tipo"],
            "dias_dh": e.get("dias_dh"), "documento_id": ids_doc.get(e.get("documento")),
            "documento_solicitud_id": ids_doc.get(e.get("documento_solicitud")),
            "fecha_solicitud": e.get("fecha_solicitud"), "fuente": _fuente(caso, e),
            "cita": e.get("cita_detalle") or e.get("cita")}


def _sincronizar_fila(cx: Connection, tabla, entidad: str, fila: dict[str, Any], resumen: dict[str, int]) -> int | None:
    """Devuelve el id del registro. Nunca toca un registro confirmado por una persona."""
    existente = cx.execute(select(tabla).where(tabla.c.clave == fila["clave"])).mappings().first()
    if existente is None:
        return None
    if existente["estado_registro"] == "confirmado":
        resumen["confirmados_intactos"] += 1
        return existente["id"]
    cambios = {k: v for k, v in fila.items() if k in existente and k != "clave" and existente[k] != v}
    if cambios:
        cx.execute(update(tabla).where(tabla.c.id == existente["id"]).values(**cambios))
        bitacora.registrar(cx, SISTEMA, "actualizar_transcripcion", entidad, existente["id"],
                           id_expediente=existente["id_expediente"], antes={k: existente[k] for k in cambios},
                           despues=cambios, motivo="Cambió la transcripción del caso real; el registro seguía propuesto.")
        resumen["actualizados"] += 1
    return existente["id"]


def sincronizar(engine: Engine, casos: dict[str, CasoReal]) -> dict[str, int]:
    resumen = {"insertados": 0, "actualizados": 0, "confirmados_intactos": 0}
    with engine.begin() as cx:
        for caso in casos.values():
            ids_doc: dict[str, int] = {}
            for d in caso.datos["documentos"]:
                fila = _fila_documento(caso, d)
                rid = _sincronizar_fila(cx, documentos, "documento", fila, resumen)
                if rid is None:
                    rid = insertar_documento(cx, SISTEMA, fila, origen="transcrito_ia", naturaleza="real",
                                             estado="propuesto", motivo=f"Caso real {caso.caso}", exigir_fecha=False)
                    resumen["insertados"] += 1
                ids_doc[d["clave"]] = rid
            for e in caso.datos.get("eventos", []):
                fila = _fila_evento(caso, e, ids_doc)
                if _sincronizar_fila(cx, eventos_plazo, "evento", fila, resumen) is None:
                    if e["tipo"] == "plazo_oficio" and e.get("dias_dh") is None:
                        continue
                    insertar_evento(cx, SISTEMA, fila, origen="transcrito_ia", naturaleza="real", estado="propuesto")
                    resumen["insertados"] += 1
    return resumen


def expediente_de(caso: CasoReal) -> Expediente:
    e = caso.datos["expediente"]
    por_clave = {d["clave"]: d for d in caso.datos["documentos"]}
    hitos = [Hito(nro=int(h["nro"]), hito=h["hito"], etapa="unica", responsable=h.get("responsable"),
                  fecha_inicio=h.get("inicio"), fecha_fin=h.get("fin"), plazo_referencial_dh=None,
                  plazo_etapa_dh=None, cuenta_plazo=h.get("cuenta_plazo"),
                  documento=(por_clave.get(h.get("documento")) or {}).get("numero"), descripcion=h.get("nota"))
             for h in caso.datos["hitos"]]
    return Expediente(id=e["id"], cod_eps="(caso real)", tipo=e["procedimiento"], fecha_inicio=e.get("fecha_inicio"),
                      plazo_maximo_dh=e.get("plazo_maximo_dh"), estado=e.get("estado"),
                      fecha_conclusion=e.get("fecha_conclusion"), hitos=hitos)


def pendientes(engine: Engine, caso: CasoReal) -> list[str]:
    """Claves de documentos y eventos del caso que una persona aún no confirmó."""
    claves = [d["clave"] for d in caso.datos["documentos"]] + [e["clave"] for e in caso.datos.get("eventos", [])]
    with engine.connect() as cx:
        estados = {r["clave"]: r["estado_registro"] for t in (documentos, eventos_plazo) for r in cx.execute(
            select(t.c.clave, t.c.estado_registro).where(t.c.clave.in_(claves))).mappings()}
    return [c for c in claves if c in estados and estados[c] != "confirmado"]
