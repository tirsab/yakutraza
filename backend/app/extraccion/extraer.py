"""Extracción de cinco campos con su cita textual y su página, y validación automática de cada cita.

Campos: número de documento, fecha, remitente, plazo en días hábiles (otorgado, solicitado o prórroga) y
requerimientos. Un campo sin cita queda vacío. Si la cita no existe literalmente en el texto de esa página,
o el valor no aparece en la cita, el campo se descarta.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.extraccion.anonimizar import plano
from app.extraccion.texto import normalizar

CAMPO = {
    "type": "object",
    "properties": {"valor": {"type": ["string", "null"]}, "cita": {"type": ["string", "null"]},
                   "pagina": {"type": ["integer", "null"]}},
    "required": ["valor", "cita", "pagina"], "additionalProperties": False,
}
ESQUEMA = {
    "type": "object",
    "properties": {
        "numero_documento": CAMPO,
        "fecha": CAMPO,
        "remitente": CAMPO,
        "plazo": {
            "type": "object",
            "properties": {"dias_habiles": {"type": ["integer", "null"]},
                           "tipo": {"type": ["string", "null"]},
                           "cita": {"type": ["string", "null"]}, "pagina": {"type": ["integer", "null"]}},
            "required": ["dias_habiles", "tipo", "cita", "pagina"], "additionalProperties": False,
        },
        "requerimientos": {"type": "array", "items": {
            "type": "object", "properties": {"texto": {"type": "string"}, "cita": {"type": ["string", "null"]},
                                             "pagina": {"type": ["integer", "null"]}},
            "required": ["texto", "cita", "pagina"], "additionalProperties": False}},
    },
    "required": ["numero_documento", "fecha", "remitente", "plazo", "requerimientos"],
    "additionalProperties": False,
}

SISTEMA = (
    "Eres un asistente que lee oficios y resoluciones de la Sunass (Perú). Extraes SOLO estos campos: número del "
    "documento, fecha, remitente (entidad u órgano, nunca una persona), plazo en días hábiles (otorgado, solicitado o "
    "prórroga; en «tipo» escribe otorgado, solicitado o prorroga) y requerimientos. Para cada campo copias la CITA TEXTUAL EXACTA del documento, carácter por carácter, "
    "y el número de página donde está. Si no hay una cita que lo respalde, deja el valor, la cita y la página en null. "
    "No inventes, no completes ni reformules. Los nombres de personas ya están reemplazados por marcas como "
    "[PERSONA_1]: no intentes adivinarlos. No decides nada: solo propones datos para que una persona los confirme."
)

NUMEROS = {"uno": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
           "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "veinte": 20,
           "treinta": 30}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def mensaje_usuario(paginas: list[str]) -> str:
    partes = [f"=== Página {i} ===\n{p}" for i, p in enumerate(paginas, 1)]
    return "Documento (texto anonimizado):\n\n" + "\n\n".join(partes)


def _compacto(t: str) -> str:
    """Cita «literal» sin depender de cómo el PDF partió las palabras («días h ábiles»): mismos caracteres en el
    mismo orden, ignorando espacios y mayúsculas."""
    return re.sub(r"\s+", "", normalizar(t)).casefold()


def _en_pagina(cita: str | None, pagina: int | None, paginas: list[str]) -> tuple[bool, str]:
    if not cita or not pagina:
        return False, "sin cita o sin página"
    if not (1 <= int(pagina) <= len(paginas)):
        return False, f"la página {pagina} no existe"
    if _compacto(cita) not in _compacto(paginas[int(pagina) - 1]):
        return False, f"la cita no aparece literalmente en la página {pagina}"
    return True, ""


def _valor_en_cita(valor: str, cita: str) -> bool:
    v, c = plano(normalizar(valor)), plano(normalizar(cita))
    if v in c:
        return True
    # Fecha: «2026-08-14» o «14/08/2026» frente a «14 de agosto de 2026».
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", v.strip())
    if m:
        a, mes, d = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(5), m.group(4))
        return str(int(d)) in c and MESES[int(mes) - 1] in c and a in c
    return False


def _dias_en_cita(dias: int, cita: str) -> bool:
    c = plano(normalizar(cita))
    if re.search(rf"(?<!\d){dias}(?!\d)", c):
        return True
    return any(n == dias and re.search(rf"\b{p}\b", c) for p, n in NUMEROS.items())


def validar(crudo: dict[str, Any], paginas: list[str]) -> dict[str, Any]:
    """Conserva solo los campos cuya cita existe literalmente y respalda el valor; el resto se descarta."""
    campos: dict[str, Any] = {}
    descartados: list[dict[str, str]] = []
    for k in ("numero_documento", "fecha", "remitente"):
        x = crudo.get(k) or {}
        if not x.get("valor"):
            campos[k] = None
            continue
        ok, motivo = _en_pagina(x.get("cita"), x.get("pagina"), paginas)
        if ok and not _valor_en_cita(str(x["valor"]), x["cita"]):
            ok, motivo = False, "el valor no aparece en la cita"
        if ok:
            campos[k] = {"valor": str(x["valor"]).strip(), "cita": x["cita"].strip(), "pagina": int(x["pagina"])}
        else:
            campos[k] = None
            descartados.append({"campo": k, "motivo": motivo})
    p = crudo.get("plazo") or {}
    if p.get("dias_habiles") is None:
        campos["plazo"] = None
    else:
        ok, motivo = _en_pagina(p.get("cita"), p.get("pagina"), paginas)
        if ok and not _dias_en_cita(int(p["dias_habiles"]), p["cita"]):
            ok, motivo = False, "los días no aparecen en la cita"
        if ok:
            campos["plazo"] = {"dias_habiles": int(p["dias_habiles"]), "tipo": p.get("tipo"), "cita": p["cita"].strip(),
                               "pagina": int(p["pagina"])}
        else:
            campos["plazo"] = None
            descartados.append({"campo": "plazo", "motivo": motivo})
    reqs = []
    for i, r in enumerate(crudo.get("requerimientos") or []):
        ok, motivo = _en_pagina(r.get("cita"), r.get("pagina"), paginas)
        if ok:
            reqs.append({"texto": str(r.get("texto", "")).strip(), "cita": r["cita"].strip(), "pagina": int(r["pagina"])})
        else:
            descartados.append({"campo": f"requerimientos[{i}]", "motivo": motivo})
    campos["requerimientos"] = reqs
    return {"campos": campos, "descartados": descartados}


def leer_fecha(t: str | None) -> date | None:
    """AAAA-MM-DD, DD/MM/AAAA o «14 de agosto de 2026» (también «setiembre»)."""
    if not t:
        return None
    t = t.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de|del)\s+(\d{4})", t.lower())
    if m and m[2].replace("setiembre", "septiembre") in MESES:
        return date(int(m[3]), MESES.index(m[2].replace("setiembre", "septiembre")) + 1, int(m[1]))
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", t)
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None
