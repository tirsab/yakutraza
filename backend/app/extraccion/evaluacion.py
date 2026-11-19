"""Evaluación independiente de la extracción contra anotaciones hechas A MANO por el equipo.

- `plantilla`: escribe DATA_DIR/extraccion/evaluacion/plantilla_anotaciones.yaml con los documentos digitales disponibles y los
  campos VACÍOS. El prototipo nunca llena los valores esperados.
- `evaluar`: lee DATA_DIR/extraccion/evaluacion/anotaciones.yaml (copia llenada por el equipo), corre la extracción y calcula
  precisión y exhaustividad por campo. El resultado queda en la misma carpeta (no se versiona).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from app.config import Settings, dir_extraccion
from app.extraccion import servicio as sv
from app.extraccion.anonimizar import plano
from app.extraccion.extraer import leer_fecha
from app.extraccion.texto import leer_pdf, normalizar

CAMPOS = ("numero_documento", "fecha", "remitente", "plazo_dias_habiles")
INSTRUCCIONES = """\
# Plantilla de anotación manual (Fase 6). La llena el EQUIPO, no el prototipo.
#
# 1. Copie este archivo como «anotaciones.yaml» en esta misma carpeta (DATA_DIR/extraccion/evaluacion/, no se versiona).
# 2. Elija 5 documentos y borre los demás. Para cada uno, abra el PDF y anote lo que dice el documento:
#    - valor: el dato (fecha en formato AAAA-MM-DD; plazo en días hábiles como número).
#    - cita: el texto exacto del documento que lo respalda.
#    - pagina: la página donde está la cita.
#    Si el documento no tiene el dato, deje los tres en null.
# 3. No escriba nombres de personas: use [PERSONA] en su lugar.
# 4. Ejecute: python -m app.cli evaluar-extraccion
"""


def carpeta(s: Settings) -> Path:
    """DATA_DIR/extraccion/evaluacion: dentro de data/ (no se versiona) y con escritura también en Docker."""
    return dir_extraccion(s) / "evaluacion"


def plantilla(s: Settings) -> Path:
    docs = []
    for d in sv.indice(s):
        doc = leer_pdf(d.ruta)
        if not doc.procesable:
            continue
        docs.append({"alias": d.alias, "id_expediente": d.id_expediente, "paginas": len(doc.paginas),
                     "campos": {k: {"valor": None, "cita": None, "pagina": None} for k in CAMPOS}})
    destino = carpeta(s) / "plantilla_anotaciones.yaml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(INSTRUCCIONES + "\n" + yaml.safe_dump({"version": 1, "documentos": docs}, allow_unicode=True,
                                                             sort_keys=False), encoding="utf-8")
    return destino


def _igual(campo: str, esperado: Any, obtenido: Any) -> bool:
    if esperado is None or obtenido is None:
        return False
    if campo == "plazo_dias_habiles":
        return int(esperado) == int(obtenido)
    if campo == "fecha":
        return leer_fecha(str(esperado)) is not None and leer_fecha(str(esperado)) == leer_fecha(str(obtenido))
    return plano(normalizar(str(esperado))) == plano(normalizar(str(obtenido)))


def _obtenido(r: dict[str, Any], campo: str) -> Any:
    c = r["campos"]
    if campo == "plazo_dias_habiles":
        return (c.get("plazo") or {}).get("dias_habiles")
    return (c.get(campo) or {}).get("valor")


def evaluar(s: Settings, extraer: Callable[[Settings, str], dict[str, Any]] = sv.extraer) -> dict[str, Any]:
    ruta = carpeta(s) / "anotaciones.yaml"
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}. Genere la plantilla con `python -m app.cli plantilla-evaluacion`, "
                                "llénela a mano y guárdela como anotaciones.yaml.")
    anot = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    por_campo = {k: {"vp": 0, "fp": 0, "fn": 0} for k in CAMPOS}
    detalle = []
    for doc in anot.get("documentos", []):
        r = extraer(s, doc["alias"])
        fila = {"alias": doc["alias"], "segundos": r.get("segundos"), "campos": {}}
        for k in CAMPOS:
            esperado = (doc.get("campos", {}).get(k) or {}).get("valor")
            obtenido = _obtenido(r, k)
            if obtenido is not None and _igual(k, esperado, obtenido):
                por_campo[k]["vp"] += 1; res = "acierto"
            elif obtenido is not None:
                por_campo[k]["fp"] += 1; res = "error" if esperado is not None else "sobra"
                if esperado is not None:
                    por_campo[k]["fn"] += 1
            elif esperado is not None:
                por_campo[k]["fn"] += 1; res = "falta"
            else:
                res = "vacío en ambos"
            fila["campos"][k] = res
        detalle.append(fila)
    for v in por_campo.values():
        v["precision"] = round(v["vp"] / (v["vp"] + v["fp"]), 3) if v["vp"] + v["fp"] else None
        v["exhaustividad"] = round(v["vp"] / (v["vp"] + v["fn"]), 3) if v["vp"] + v["fn"] else None
    vp, fp, fn = (sum(v[x] for v in por_campo.values()) for x in ("vp", "fp", "fn"))
    res = {"documentos": len(detalle), "por_campo": por_campo,
           "total": {"vp": vp, "fp": fp, "fn": fn, "precision": round(vp / (vp + fp), 3) if vp + fp else None,
                     "exhaustividad": round(vp / (vp + fn), 3) if vp + fn else None},
           "detalle": detalle, "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "proveedor": s.extraccion_proveedor}
    destino = carpeta(s) / "resultado.yaml"
    destino.write_text(yaml.safe_dump(res, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return res
