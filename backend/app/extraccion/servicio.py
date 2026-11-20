"""Índice de documentos reales (por alias, nunca por nombre de archivo) y flujo completo de extracción.

Los PDF están en la parte privada de los casos reales (DATA_DIR/casos_reales/<carpeta>/). Sus nombres de
archivo pueden contener nombres de personas: la API y la interfaz solo usan alias como «TACNA-07».
El índice y los resultados se guardan en EXTRACCION_DIR (dentro de DATA_DIR: no se versiona).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings, dir_extraccion, dir_privado
from app.extraccion import extraer as ext
from app.extraccion.anonimizar import Anonimizador, lista_privada
from app.extraccion.proveedores import ErrorProveedor, Proveedor, crear
from app.extraccion.texto import leer_pdf, limpiar

# Palabra de la carpeta → (prefijo del alias, expediente del caso real).
CASOS = {"TACNA": ("TACNA", "REAL-TACNA-2026"), "EPSSMU": ("EPSSMU", "REAL-EPSSMU-2025"),
         "PASCO": ("PASCO", "REAL-PASCO-2024")}
NOMBRES_A_OCULTAR = "nombres_a_ocultar.txt"
# Documentos publicados oficialmente (por nombre de archivo). Solo estos pueden ir a una API externa (Anthropic):
# los oficios intermedios, aun anonimizados, se leen solo con el modelo local.
PUBLICADOS = (re.compile(r"(?i)^RCD 032-2026"),)
# También es publicado un PDF que es una página de El Peruano (separatas Normas Legales o Proyectos; p. ej. RD 015-2024,
# RCD 060-2024 y RCD 076-2024 de Pasco): se reconoce por la cabecera de página («Sábado 28 de setiembre de 2024 El
# Peruano»), no por el nombre del archivo.
SEPARATA = (re.compile(r"(?i)(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\s+\d{1,2}\s+de\s+[a-záéíóú]+"
                       r"\s+de\s+\d{4}\s*El\s*Peruano"),)


def es_separata_el_peruano(ruta: Path) -> bool:
    try:
        primera = leer_pdf(ruta).paginas[0]
    except Exception:  # noqa: BLE001 (un PDF ilegible no es publicado)
        return False
    return all(p.search(primera) for p in SEPARATA)


class ErrorPrivacidad(RuntimeError):
    pass


@dataclass(frozen=True)
class DocReal:
    alias: str
    id_expediente: str | None
    ruta: Path      # nunca sale de este módulo
    sha256: str
    publicado: bool = False  # resolución publicada (por nombre o por ser una página de El Peruano)

    def publico(self) -> dict[str, Any]:
        return {"alias": self.alias, "id_expediente": self.id_expediente, "huella": self.sha256[:12],
                "publicado": self.publicado}


def indice(s: Settings) -> list[DocReal]:
    """Documentos PDF de los casos reales. Vacío si CASOS_REALES_PRIVADOS=false."""
    base = dir_privado(s)
    if base is None or not Path(base).exists():
        return []
    docs = []
    # Orden por nombre sin distinguir mayúsculas: igual en Windows y en Linux (Docker), para que el alias no cambie.
    for carpeta in sorted((p for p in Path(base).iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
        clave = next(((pref, exp) for k, (pref, exp) in CASOS.items() if k in carpeta.name.upper()), None)
        if clave is None:
            continue
        # También en subcarpetas (Pasco) y con extensión .PDF; orden por la ruta relativa.
        pdfs = sorted((p for p in carpeta.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"),
                      key=lambda p: str(p.relative_to(carpeta)).replace("\\", "/").casefold())
        for i, pdf in enumerate(pdfs, 1):
            pub = any(p.search(pdf.name) for p in PUBLICADOS) or es_separata_el_peruano(pdf)
            docs.append(DocReal(f"{clave[0]}-{i:02d}", clave[1], pdf, hashlib.sha256(pdf.read_bytes()).hexdigest(), pub))
    return docs


def buscar(s: Settings, alias: str) -> DocReal:
    for d in indice(s):
        if d.alias == alias:
            return d
    raise LookupError(f"No existe el documento {alias} (o la parte privada no está habilitada).")


def ruta_lista_privada(s: Settings) -> Path | None:
    base = dir_privado(s)
    return Path(base) / NOMBRES_A_OCULTAR if base is not None else None


def proveedor_de(s: Settings) -> Proveedor | None:
    return crear(s.extraccion_proveedor, ollama_url=s.ollama_url, ollama_modelo=s.ollama_modelo,
                 anthropic_modelo=s.anthropic_modelo)


def texto_anonimizado(s: Settings, d: DocReal) -> dict[str, Any]:
    """Texto limpio y anonimizado por página. Si queda un nombre de la lista privada o un sello de firma, se detiene."""
    doc = leer_pdf(d.ruta)
    paginas = limpiar(doc.paginas)
    an = Anonimizador(lista_privada(ruta_lista_privada(s)))
    r = an.anonimizar(paginas)
    if not r.seguro:
        raise ErrorPrivacidad(f"{d.alias}: después de anonimizar siguen apareciendo {len(r.pendientes)} nombres de la "
                              f"lista privada y {r.restos} sellos de firma con nombre. El documento no se procesa.")
    return {"paginas": r.paginas, "requiere_ocr": doc.requiere_ocr, "procesable": doc.procesable,
            "reemplazos": r.reemplazos}


def extraer(s: Settings, alias: str, proveedor: Proveedor | None = None) -> dict[str, Any]:
    d = buscar(s, alias)
    proveedor = proveedor or proveedor_de(s)
    if proveedor is None:
        raise ErrorProveedor("La extracción con IA está desactivada. Configure EXTRACCION_PROVEEDOR=ollama (modelo local) "
                             "o anthropic (solo texto anonimizado) en .env.")
    if proveedor.nombre == "anthropic" and not d.publicado:
        raise ErrorPrivacidad(f"{alias} no es un documento publicado: la API de Anthropic solo recibe textos públicos o "
                              "sintéticos. Léalo con el modelo local (EXTRACCION_PROVEEDOR=ollama).")
    t = texto_anonimizado(s, d)
    if not t["procesable"]:
        raise ErrorProveedor(f"{alias} parece un escaneo sin texto: requiere OCR, que está fuera del alcance.")
    inicio = time.monotonic()
    crudo = proveedor.extraer(ext.SISTEMA, ext.mensaje_usuario(t["paginas"]), ext.ESQUEMA)
    validado = ext.validar(crudo, t["paginas"])
    res = {**d.publico(), **validado, "proveedor": proveedor.nombre, "modelo": proveedor.modelo,
           "segundos": round(time.monotonic() - inicio, 1), "paginas": len(t["paginas"]),
           "requiere_ocr": t["requiere_ocr"], "reemplazos": t["reemplazos"],
           "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "aviso": "Propuesto por IA: nada entra al expediente hasta que una persona lo confirme."}
    carpeta = dir_extraccion(s)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{alias}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


def ultimo(s: Settings, alias: str) -> dict[str, Any] | None:
    f = dir_extraccion(s) / f"{alias}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
