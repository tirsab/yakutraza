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


def difundidos(s: Settings) -> set[str]:
    """Huellas (SHA-256 del PDF) de documentos que una resolución publicada manda difundir (rules/privacidad_revisado.yaml).
    Su texto puede citarse en el repositorio; no cambia qué puede ir a una API externa."""
    import yaml
    ruta = Path(s.rules_dir) / "privacidad_revisado.yaml"
    if not ruta.exists():
        return set()
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return {x["sha256"] for x in datos.get("documentos_difundidos", [])}


def _palabras(t: str) -> list[str]:
    return re.findall(r"[a-z0-9ñ]+", plano(normalizar(t)))


def _fragmentos(t: str) -> set[str]:
    p = _palabras(t)
    return {" ".join(p[i:i + N_PALABRAS]) for i in range(len(p) - N_PALABRAS + 1)}


def archivos_versionados(raiz: Path = RAIZ_REPO) -> list[Path]:
    r = subprocess.run(["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=True)
    return [raiz / x for x in r.stdout.splitlines() if (raiz / x).suffix.lower() in SUFIJOS_TEXTO and (raiz / x).exists()]


# Documentos publicados oficialmente (su texto puede citarse en los archivos públicos del repositorio).
PUBLICADOS = sv.PUBLICADOS


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
        if d.publicado or d.sha256 in difundidos(s):
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


# ------------------------------------------------------------------ rastros por patrón (no necesita los PDF privados)
from app.extraccion.anonimizar import CORREO, nombre_en, restos_de_firma  # noqa: E402

# Nombres visiblemente inventados de las pruebas: no son rastros.
INVENTADOS = re.compile(r"(?i)fictici|inventad|prueba|nombrea|apellidob|ñandú|ñandu")
CORREOS_PERMITIDOS = {"ejemplo@ejemplo.pe", "noreply@anthropic.com"}
CABECERA_REPO = re.compile(r"(?m)^[ \t]*(?:PARA|DE|A)[ \t]*:[ \t]*(.+)$")  # solo en mayúsculas, como en los oficios
ENLACE_PRIVADO = re.compile(r"(?i)drive\.google\.com|docs\.google\.com|wetransfer\.com|onedrive\.live\.com")


def rastros(texto: str) -> list[str]:
    """Tipos de rastro de un oficio en un texto: sello de firma, cabecera con nombre, correo o enlace privado."""
    tipos = []
    sin_inventados = "\n".join(ln for ln in texto.split("\n") if not INVENTADOS.search(ln))
    if restos_de_firma(sin_inventados):
        tipos.append("sello_de_firma")
    if any(nombre_en(m.group(1)) for m in CABECERA_REPO.finditer(sin_inventados)):
        tipos.append("cabecera_con_nombre")
    if {c.lower() for c in CORREO.findall(sin_inventados)} - CORREOS_PERMITIDOS:
        tipos.append("correo")
    if ENLACE_PRIVADO.search(texto):
        tipos.append("enlace_privado")
    return tipos


def archivos_a_revisar() -> list[Path]:
    """Archivos versionados (git ls-files). Sin git (por ejemplo, dentro del contenedor, donde no está el repositorio
    completo): los archivos de texto de las carpetas montadas, es decir, reglas, casos reales públicos y backend."""
    try:
        return archivos_versionados()
    except (OSError, subprocess.CalledProcessError):
        from app.config import get_settings
        s = get_settings()
        raices = [Path(s.rules_dir), Path(s.casos_reales_dir), Path(__file__).resolve().parents[2]]
        return [f for r in raices if r.exists() for f in r.rglob("*")
                if f.is_file() and f.suffix.lower() in SUFIJOS_TEXTO and f.suffix
                and not any(x in f.parts for x in (".venv", "node_modules", "__pycache__", ".pytest_cache"))]


def rastros_en_repo(archivos: list[Path] | None = None) -> list[Hallazgo]:
    """Revisa los archivos versionados con los patrones de `rastros` (corre sin la parte privada)."""
    hallazgos = []
    for f in archivos if archivos is not None else archivos_a_revisar():
        try:
            texto = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(f.relative_to(RAIZ_REPO)) if f.is_relative_to(RAIZ_REPO) else str(f)
        hallazgos += [Hallazgo(rel, t) for t in rastros(texto)]
    return hallazgos


def verificar_historial(s: Settings, raiz: Path = RAIZ_REPO) -> list[tuple[str, str, str]]:
    """Busca en TODO el historial git (todas las ramas) los nombres que el anonimizador reconoce en los PDF de los
    casos reales y los de la lista privada. Devuelve (ruta en el repo, tipo, huella del nombre); nunca el nombre."""
    from app.extraccion.anonimizar import Anonimizador
    nombres: dict[str, str] = {plano(n): "lista_privada" for n in lista_privada(sv.ruta_lista_privada(s))}
    for d in sv.indice(s):
        an = Anonimizador()
        an.anonimizar(leer_pdf(d.ruta).paginas)
        for n in an.alias:
            if len(n) >= 6:
                nombres.setdefault(n, "anonimizador")
    salida = subprocess.run(["git", "rev-list", "--all", "--objects"], cwd=raiz, capture_output=True, text=True,
                            encoding="utf-8", check=True).stdout.splitlines()
    rutas = {}
    for ln in salida:
        partes = ln.split(" ", 1)
        if len(partes) == 2:
            rutas.setdefault(partes[0], partes[1])
    encontrados = []
    for obj, ruta in rutas.items():
        if Path(ruta).suffix.lower() not in SUFIJOS_TEXTO:
            continue
        r = subprocess.run(["git", "cat-file", "-p", obj], cwd=raiz, capture_output=True)
        if r.returncode != 0:
            continue
        t = plano(r.stdout.decode("utf-8", "ignore"))
        for n, tipo in nombres.items():
            if re.search(r"\b" + re.escape(n).replace(r"\ ", r"\s+") + r"\b", t):
                encontrados.append((ruta, tipo, huella(n)[:12]))
        tipos = rastros(r.stdout.decode("utf-8", "ignore"))
        encontrados += [(ruta, t2, "-") for t2 in tipos]
    return sorted(set(encontrados))
