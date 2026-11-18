"""Anonimización ANTES de cualquier procesamiento (también con el modelo local).

Reemplaza nombres de personas por [PERSONA_1], [PERSONA_2]…, y DNI, correos y teléfonos por marcas.
Los nombres se detectan por:
- una lista privada que mantiene el equipo (DATA_DIR/casos_reales/nombres_a_ocultar.txt, no versionada);
- tratamientos y cargos seguidos de nombres propios (Sr., Ing., Abog., CPC…);
- líneas de nombre en mayúsculas cerca de «Atentamente».
Si después de anonimizar queda algún nombre de la lista privada, el documento NO se procesa.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

PALABRA_NOMBRE = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+|[A-ZÁÉÍÓÚÑ]{2,}"
TRATAMIENTO = (r"(?:Sr\.|Sra\.|Srta\.|Señor(?:a|ita)?|Ing\.|Ingenier[oa]|Abog\.|Abogad[oa]|Lic\.|Licenciad[oa]|"
               r"C\.?P\.?C\.?|Econ\.|Economista|Dr\.|Dra\.|Doctor(?:a)?|Mg\.|Mag\.|Magíster|Arq\.|Arquitect[oa]|"
               r"Bach\.|Tec\.)")
CON_TRATAMIENTO = re.compile(rf"\b{TRATAMIENTO}\s+((?:(?:{PALABRA_NOMBRE})(?:\s+|$)){{2,5}})")
DNI = re.compile(r"(?i)\b(DNI|D\.N\.I\.)\s*(N[°º.]?\s*)?:?\s*\d{8}\b")
CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
TELEFONO = re.compile(r"(?<!\d)(?:\+?51[\s-]?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)")
# Palabras en mayúsculas que NO son nombres de personas (cargos, entidades, siglas frecuentes en los oficios).
NO_NOMBRES = {"GERENTE", "GENERAL", "SUNASS", "EPS", "S.A.", "SA", "DIRECCION", "DIRECCIÓN", "DIRECTOR", "DIRECTORA",
              "REGULACION", "REGULACIÓN", "TARIFARIA", "ECONOMICA", "ECONÓMICA", "SUBDIRECCION", "SUBDIRECCIÓN",
              "OFICIO", "INFORME", "MEMORANDO", "RESOLUCION", "RESOLUCIÓN", "CONSEJO", "DIRECTIVO", "PRESIDENTE",
              "ASUNTO", "REFERENCIA", "ATENTAMENTE", "TACNA", "LIMA", "PERU", "PERÚ", "EPSSMU", "DRT", "DRE", "SRT",
              "OAJ", "GG", "DEL", "DE", "LA", "LOS", "LAS", "Y", "PARA", "EL", "CON", "PROGRAMA", "INVERSIONES",
              "FONDO", "RESERVA", "AGUA", "POTABLE", "ALCANTARILLADO", "SANEAMIENTO", "EMPRESA", "PRESTADORA"}


def plano(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def lista_privada(ruta: Path | None) -> list[str]:
    """Nombres que el equipo quiere ocultar siempre (uno por línea; # para comentarios)."""
    if ruta is None or not Path(ruta).exists():
        return []
    return [ln.strip() for ln in Path(ruta).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


@dataclass
class Resultado:
    paginas: list[str]
    reemplazos: dict[str, int] = field(default_factory=dict)  # tipo → cuántos (nunca los valores)
    pendientes: list[str] = field(default_factory=list)        # nombres de la lista privada que siguen presentes

    @property
    def seguro(self) -> bool:
        return not self.pendientes


class Anonimizador:
    def __init__(self, nombres_privados: list[str] | None = None):
        self.privados = sorted({n for n in (nombres_privados or []) if len(n) >= 4}, key=len, reverse=True)
        self.alias: dict[str, str] = {}

    def _persona(self, nombre: str) -> str:
        clave = plano(re.sub(r"\s+", " ", nombre.strip()))
        if clave not in self.alias:
            self.alias[clave] = f"[PERSONA_{len(self.alias) + 1}]"
        return self.alias[clave]

    def _privados(self, t: str, cuenta: dict[str, int]) -> str:
        for n in self.privados:
            # Coincidencia sin distinguir mayúsculas ni tildes, con espacios flexibles.
            patron = r"\s+".join(_patron_palabra(p) for p in n.split())
            t, k = re.subn(patron, lambda m: self._persona(m.group(0)), t)
            cuenta["lista_privada"] = cuenta.get("lista_privada", 0) + k
        return t

    def _tratamientos(self, t: str, cuenta: dict[str, int]) -> str:
        def sub(m: re.Match) -> str:
            nombre = m.group(1).strip()
            palabras = [p for p in nombre.split() if p.upper().strip(".,") not in NO_NOMBRES]
            if len(palabras) < 2:
                return m.group(0)
            cuenta["tratamiento"] = cuenta.get("tratamiento", 0) + 1
            return m.group(0).replace(nombre, self._persona(nombre))
        return CON_TRATAMIENTO.sub(sub, t)

    def _firmas_en_mayusculas(self, t: str, cuenta: dict[str, int]) -> str:
        lineas = t.split("\n")
        for i, ln in enumerate(lineas):
            if re.search(r"(?i)\batentamente\b", ln):
                for j in range(i + 1, min(i + 6, len(lineas))):
                    palabras = lineas[j].split()
                    if (2 <= len(palabras) <= 5 and all(re.fullmatch(r"[A-ZÁÉÍÓÚÑ.]{2,}", p) for p in palabras)
                            and not any(p.strip(".") in NO_NOMBRES for p in palabras)):
                        cuenta["firma"] = cuenta.get("firma", 0) + 1
                        lineas[j] = self._persona(lineas[j])
        return "\n".join(lineas)

    def anonimizar(self, paginas: list[str]) -> Resultado:
        cuenta: dict[str, int] = {}
        res = []
        for p in paginas:
            t = self._privados(p, cuenta)
            t = self._tratamientos(t, cuenta)
            t = self._firmas_en_mayusculas(t, cuenta)
            t, k = DNI.subn("[DNI]", t); cuenta["dni"] = cuenta.get("dni", 0) + k
            t, k = CORREO.subn("[CORREO]", t); cuenta["correo"] = cuenta.get("correo", 0) + k
            t, k = TELEFONO.subn("[TELÉFONO]", t); cuenta["telefono"] = cuenta.get("telefono", 0) + k
            res.append(t)
        texto = plano(" ".join(res))
        pendientes = [n for n in self.privados if plano(n) in texto]
        return Resultado(paginas=res, reemplazos={k: v for k, v in cuenta.items() if v}, pendientes=pendientes)


def _sin_tilde(c: str) -> str:
    return "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x))


def _patron_palabra(p: str) -> str:
    """Patrón de una palabra sin distinguir mayúsculas ni tildes («María» también encuentra «MARIA»)."""
    partes = []
    for c in p:
        if c.isalpha():
            variantes = {c.lower(), c.upper(), _sin_tilde(c).lower(), _sin_tilde(c).upper()}
            partes.append("[" + "".join(re.escape(v) for v in sorted(variantes)) + "]")
        else:
            partes.append(re.escape(c))
    return "".join(partes)
