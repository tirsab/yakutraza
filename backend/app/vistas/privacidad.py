"""Lo que una EPS no ve: documentos internos de Sunass (informes y memorandos, en borrador o no)."""

from __future__ import annotations

import re
from typing import Any

INTERNO = re.compile(r"^(INF|MEM)\b|^(Informe|Memorando|Memorándum)\b", re.IGNORECASE)
TEXTO = "Documento interno de Sunass"


def _es_interno(ref: Any) -> bool:
    return isinstance(ref, str) and bool(INTERNO.match(ref.strip()))


def ocultar_internos(f: dict[str, Any]) -> dict[str, Any]:
    """Copia de la ficha sin documentos reservados ni referencias a informes o memorandos."""
    ocultos = {d["id"] for d in f["documentos"] if d.get("reservado") or _es_interno(d.get("numero"))
               or d.get("tipo") in ("INF", "MEM")}
    g = dict(f)
    g["documentos"] = [d for d in f["documentos"] if d["id"] not in ocultos]
    linea = []
    for h in f["linea_de_tiempo"]:
        ev = dict(h["evidencia"])
        ev["documentos"] = [i for i in ev.get("documentos", []) if i not in ocultos]
        for k in ("referencia", "codigo_ds02"):
            if _es_interno(ev.get(k)):
                ev[k] = TEXTO
        linea.append({**h, "evidencia": ev, "alertas": [_alerta(a) for a in h.get("alertas", [])]})
    g["linea_de_tiempo"] = linea
    g["relojes"] = [_alerta(a) for a in f["relojes"]]
    g["bitacora"] = [b for b in f["bitacora"]
                     if not (b.get("entidad") == "documento" and str(b.get("entidad_id")) in {str(i) for i in ocultos})]
    g["vista"] = "eps"
    return g


def _alerta(a: dict[str, Any]) -> dict[str, Any]:
    if _es_interno(a.get("documento_inicio")):
        a = {**a, "documento_inicio": TEXTO}
    return a
