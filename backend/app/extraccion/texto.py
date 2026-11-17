"""Texto de un PDF por página, con limpieza de marcas de agua, encabezados repetidos y bloques de firma."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# pypdf avisa de fuentes que no puede describir del todo; no afecta al texto extraído.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# Menos caracteres que esto en una página: probablemente es un escaneo y necesita OCR (fuera del alcance).
MIN_CARACTERES_PAGINA = 80

# Rastros de una firma digital: no aportan datos y suelen traer nombres de personas.
FIRMA = re.compile(r"(?i)(firmado digitalmente|firma digital|motivo\s*:|soy el autor del documento|"
                   r"\bfau\s*\d{11}|\bfecha\s*:\s*\d{4}[/-]\d{2}[/-]\d{2}\s+\d{2}:\d{2})")


@dataclass
class Documento:
    paginas: list[str]
    requiere_ocr: list[int] = field(default_factory=list)  # números de página (desde 1)

    @property
    def procesable(self) -> bool:
        return any(len(p.strip()) >= MIN_CARACTERES_PAGINA for p in self.paginas)


def normalizar(t: str) -> str:
    """Normalización para comparar citas: NFC, comillas y guiones simples, espacios colapsados."""
    t = unicodedata.normalize("NFC", t)
    t = t.replace("­", "").replace(" ", " ")
    t = re.sub(r"[“”«»]", '"', t)
    t = re.sub(r"[‘’]", "'", t)
    t = re.sub(r"[‐‑‒–—]", "-", t)
    return re.sub(r"\s+", " ", t).strip()


def leer_pdf(ruta: Path) -> Documento:
    lector = PdfReader(str(ruta))
    paginas = [(p.extract_text() or "") for p in lector.pages]
    return Documento(paginas=paginas,
                     requiere_ocr=[i + 1 for i, p in enumerate(paginas) if len(p.strip()) < MIN_CARACTERES_PAGINA])


def limpiar(paginas: list[str]) -> list[str]:
    """Quita encabezados y pies que se repiten, bloques de firma y cortes de palabra al final de línea."""
    lineas_por_pagina = [[ln.strip() for ln in p.splitlines()] for p in paginas]
    repetidas: set[str] = set()
    if len(paginas) > 1:
        cuenta = Counter(ln for lns in lineas_por_pagina for ln in set(lns) if ln)
        umbral = max(2, int(0.6 * len(paginas)))
        repetidas = {ln for ln, n in cuenta.items() if n >= umbral and len(ln) < 120}
    limpias = []
    for lns in lineas_por_pagina:
        buenas = [ln for ln in lns if ln and ln not in repetidas and not FIRMA.search(ln)]
        texto = "\n".join(buenas)
        texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)       # palabra cortada al final de línea
        texto = re.sub(r"[ \t]+", " ", texto)
        limpias.append(texto.strip())
    return limpias
