"""Verificación de privacidad del repositorio: ningún texto de los oficios llega a los archivos versionados.

Revisa cada archivo versionado (git ls-files) contra:
- los nombres de la lista privada (nombres_a_ocultar.txt);
- fragmentos de 8 palabras seguidas tomados del texto de cualquier PDF de los casos reales;
- los nombres de archivo de esos PDF (algunos contienen nombres de personas).
Informa archivo y tipo de coincidencia, nunca el texto encontrado.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import RAIZ_REPO, Settings
from app.extraccion import servicio as sv
from app.extraccion.anonimizar import lista_privada, plano
from app.extraccion.texto import leer_pdf, normalizar

N_PALABRAS = 8
SUFIJOS_TEXTO = {".py", ".ts", ".tsx", ".md", ".yaml", ".yml", ".json", ".css", ".html", ".txt", ".toml", ".ini",
                 ".cfg", ".ps1", ".sh", ".example", ".conf", ""}


@dataclass
class Hallazgo:
    archivo: str
    tipo: str  # nombre_privado | fragmento_de_oficio | nombre_de_archivo
    fragmentos: tuple[str, ...] = ()  # solo para revisar en la consola (--revisar); nunca se guardan


def huella(fragmento: str) -> str:
    return hashlib.sha256(fragmento.encode("utf-8")).hexdigest()


def revisados(s: Settings) -> set[str]:
    """Huellas (SHA-256) de fragmentos que una persona revisó y aprobó (rules/privacidad_revisado.yaml)."""
    import yaml
    ruta = Path(s.rules_dir) / "privacidad_revisado.yaml"
    if not ruta.exists():
        return set()
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return {x["sha256"] for x in datos.get("fragmentos", [])}


def _palabras(t: str) -> list[str]:
    return re.findall(r"[a-z0-9ñ]+", plano(normalizar(t)))


def _fragmentos(t: str) -> set[str]:
    p = _palabras(t)
    return {" ".join(p[i:i + N_PALABRAS]) for i in range(len(p) - N_PALABRAS + 1)}


def archivos_versionados(raiz: Path = RAIZ_REPO) -> list[Path]:
    r = subprocess.run(["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=True)
    return [raiz / x for x in r.stdout.splitlines() if (raiz / x).suffix.lower() in SUFIJOS_TEXTO and (raiz / x).exists()]


# Documentos publicados oficialmente (su texto puede citarse en los archivos públicos del repositorio).
PUBLICADOS = (re.compile(r"(?i)^RCD 032-2026"),)


def _normas() -> list[Path]:
    """Copias locales de las normas (docs/normas/*.pdf, no versionadas), en este checkout o en el principal."""
    carpetas = [RAIZ_REPO / "docs" / "normas"]
    if len(RAIZ_REPO.parents) >= 3:
        carpetas.append(RAIZ_REPO.parents[2] / "docs" / "normas")
    return [f for c in carpetas if c.exists() for f in c.glob("*.pdf")]


def _nombre_sospechoso(stem: str) -> str | None:
    """El nombre de archivo completo, si tiene 3 o más palabras seguidas que no son parte de un número de documento."""
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}", stem)
    comunes = {"oficio", "informe", "memorando", "rcd", "sunass", "dre", "srt", "drt", "eps", "tacna", "epssmu",
               "uso", "del", "notificacion", "notificación", "excepcional"}
    resto = [p for p in palabras if p.lower() not in comunes]
    return plano(stem) if len(resto) >= 3 else None


def verificar(s: Settings, archivos: list[Path] | None = None) -> list[Hallazgo]:
    """Solo cuenta el texto PROPIO de un documento intermedio: fragmentos que no están en normas ni en resoluciones
    publicadas, y que aparecen en un solo documento (las frases institucionales se repiten entre documentos)."""
    docs = sv.indice(s)
    nombres = [plano(n) for n in lista_privada(sv.ruta_lista_privada(s))]
    publicos: set[str] = set()
    for f in _normas():
        for p in leer_pdf(f).paginas:
            publicos |= _fragmentos(p)
    por_doc: dict[str, set[str]] = {}
    for d in docs:
        fr: set[str] = set()
        for p in leer_pdf(d.ruta).paginas:
            fr |= _fragmentos(p)
        if any(pat.search(d.ruta.name) for pat in PUBLICADOS):
            publicos |= fr
        else:
            por_doc[d.alias] = fr
    conteo: dict[str, int] = {}
    for fr in por_doc.values():
        for x in fr:
            conteo[x] = conteo.get(x, 0) + 1
    aprobados = revisados(s)
    propios = {x for x, n in conteo.items() if n == 1 and x not in publicos and huella(x) not in aprobados}
    stems = {n for d in docs if (n := _nombre_sospechoso(d.ruta.stem))}
    hallazgos = []
    for f in archivos if archivos is not None else archivos_versionados():
        try:
            texto = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        t = plano(texto)
        rel = str(f.relative_to(RAIZ_REPO)) if f.is_relative_to(RAIZ_REPO) else str(f)
        if any(n and n in t for n in nombres):
            hallazgos.append(Hallazgo(rel, "nombre_privado"))
        comunes = _fragmentos(texto) & propios if propios else set()
        if comunes:
            hallazgos.append(Hallazgo(rel, "fragmento_de_oficio", tuple(sorted(comunes))))
        if any(st in t for st in stems):
            hallazgos.append(Hallazgo(rel, "nombre_de_archivo"))
    return hallazgos
