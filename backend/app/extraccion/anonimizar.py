"""Anonimización ANTES de cualquier procesamiento (también con el modelo local).

Reemplaza nombres de personas por [PERSONA_1], [PERSONA_2]…, y DNI, correos y teléfonos por marcas.
Los nombres se detectan por:
- una lista privada que mantiene el equipo (DATA_DIR/casos_reales/nombres_a_ocultar.txt, no versionada);
- tratamientos y cargos seguidos de nombres propios (Sr., Ing., Abog., CPC…);
- líneas de nombre en mayúsculas cerca de «Atentamente»;
- cabeceras de memorandos y oficios: «PARA :», «DE :», «A :», «Señor(a):» (el nombre puede ir en la línea siguiente);
- sellos de firma digital: nombre seguido de fecha y hora («NOMBRE FICTICIO23/09/2099 17:09:03»);
- «Firmado digitalmente por: NOMBRE»;
- firmantes en las líneas que siguen a «Regístrese…», «Comuníquese…» o «Publíquese…».
Si después de anonimizar queda algún nombre de la lista privada, o un sello de firma con nombre, el documento NO se
procesa.
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
              "FONDO", "RESERVA", "AGUA", "POTABLE", "ALCANTARILLADO", "SANEAMIENTO", "EMPRESA", "PRESTADORA",
              # cargos, oficinas y palabras de la estructura de los documentos (no son nombres de personas)
              "GERENCIA", "GERENTA", "EJECUTIVO", "EJECUTIVA", "SUBDIRECTOR", "SUBDIRECTORA", "PRESIDENTA", "JEFE",
              "JEFA", "OFICINA", "ASESORIA", "ASESORÍA", "JURIDICA", "JURÍDICA", "DESCONCENTRADA", "SERVICIOS",
              "SUPERINTENDENCIA", "NACIONAL", "ADMINISTRACION", "ADMINISTRACIÓN", "UNIDAD", "AREA", "ÁREA",
              "COORDINADOR", "COORDINADORA", "ESPECIALISTA", "ANALISTA", "ASESOR", "ASESORA", "SECRETARIO",
              "SECRETARIA", "TECNICO", "TÉCNICO", "TECNICA", "TÉCNICA", "OPERACIONES", "COMERCIAL", "PLANEAMIENTO",
              "PRESUPUESTO", "FINANZAS", "ANEXO", "ANEXOS", "EXPOSICION", "EXPOSICIÓN", "MOTIVOS", "CUADRO",
              "TOTAL", "SUBTOTAL", "FUENTE", "ELABORACION", "ELABORACIÓN", "PERUANO", "NORMAS", "LEGALES",
              "MUNICIPAL", "PROVINCIAL", "REGIONAL", "MINISTERIO", "VIVIENDA", "CONSTRUCCION", "CONSTRUCCIÓN",
              "OTASS", "ODS", "DU", "DS", "RD", "RCD", "CD", "S.A", "EIRL", "SAC", "N°", "N.°", "NRO", "PASCO",
              "EMAPA", "VICCO", "AMAZONAS", "UTCUBAMBA", "BAGUA", "GRANDE", "PRESENTE", "FIRMADO", "DIGITALMENTE",
              "POR", "EN", "AL", "A", "O", "U", "E"}
# Partículas que pueden ir dentro de un nombre («María de los Ángeles»).
PARTICULAS = {"de", "del", "la", "las", "los", "y"}
# Palabra con forma de nombre propio: «Nombre», «NOMBRE» o «Ñ.» (inicial).
TOKEN_NOMBRE = r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü'.-]*"
# Fecha y hora de un sello de firma digital (pegada o no al nombre).
FECHA_HORA = r"\d{1,2}/\d{1,2}/\d{4}\s*\d{1,2}:\d{2}"
# El nombre puede ir en la misma línea que la fecha o en la línea anterior.
SELLO = re.compile(rf"((?:{TOKEN_NOMBRE}[ \t]+){{0,5}}{TOKEN_NOMBRE})[ \t]*\n?[ \t]*(?={FECHA_HORA})")
# Cargos que suelen ir en la línea siguiente al nombre de quien firma.
CARGO = re.compile(r"(?i)^\s*(gerente|gerenta|jef[ea]|director[a]?|subdirector[a]?|president[ea]|especialista|"
                   r"coordinador[a]?|analista|asesor[a]?|secretari[oa]|superintendente|intendente|administrador[a]?|"
                   r"encargad[oa]|responsable)\b")
CABECERA = re.compile(r"(?i)^[ \t]*(PARA|DE|A|SE(?:Ñ|N)OR(?:A|ITA)?|SE(?:Ñ|N)OR\(A\))[ \t]*:[ \t]*(.*)$")
FIRMADO_POR = re.compile(rf"(?i)(firmado\s+(?:digitalmente\s+)?por\s*:?[ \t]*)((?:{TOKEN_NOMBRE}[ \t]*){{2,6}})")
CIERRE = re.compile(r"(?i)\b(reg[íi]strese|comun[íi]quese|publ[íi]quese)\b")


def _es_nombre(palabra: str) -> bool:
    return bool(re.fullmatch(TOKEN_NOMBRE, palabra)) and palabra.upper().strip(".,;:") not in NO_NOMBRES


def nombre_en(texto: str, minimo: int = 2) -> tuple[int, int] | None:
    """Posición (inicio, fin) del primer tramo con forma de nombre de persona: 2 a 6 palabras con mayúscula inicial
    que no son cargos ni oficinas, con partículas («de», «del»…) permitidas en medio. None si no hay."""
    palabras = list(re.finditer(r"\S+", texto))
    i = 0
    while i < len(palabras):
        if not _es_nombre(palabras[i].group(0)):
            i += 1
            continue
        j, n, fin = i, 0, i
        while j < len(palabras) and j - i < 8:
            w = palabras[j].group(0)
            if _es_nombre(w):
                n, fin = n + 1, j
            elif w.lower() not in PARTICULAS:
                break
            j += 1
        if n >= minimo:
            return palabras[i].start(), palabras[fin].end()
        i = j if j > i else i + 1
    return None


def _separar_fecha(t: str) -> str:
    """«APELLIDO23/09/2026 17:09» → «APELLIDO 23/09/2026 17:09» (el PDF suele pegar el nombre a la fecha)."""
    return re.sub(rf"([A-Za-zÁÉÍÓÚÑáéíóúñü])(?={FECHA_HORA})", r"\1 ", t)


def restos_de_firma(texto: str) -> int:
    """Sellos de firma (nombre + fecha y hora) que siguen con forma de nombre: si hay alguno, no es seguro."""
    return sum(1 for m in SELLO.finditer(_separar_fecha(texto)) if nombre_en(m.group(1)) is not None)


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
    restos: int = 0                                             # sellos de firma con nombre que siguen presentes

    @property
    def seguro(self) -> bool:
        return not self.pendientes and not self.restos


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

    def _reemplazar_nombre(self, texto: str, cuenta: dict[str, int], tipo: str) -> str:
        pos = nombre_en(texto)
        if pos is None:
            return texto
        a, b = pos
        cuenta[tipo] = cuenta.get(tipo, 0) + 1
        return texto[:a] + self._persona(texto[a:b]) + texto[b:]

    def _cabeceras(self, t: str, cuenta: dict[str, int]) -> str:
        """«PARA : NOMBRE», «DE : Nombre» (o el nombre en la línea siguiente si la cabecera queda vacía)."""
        lineas = t.split("\n")
        for i, ln in enumerate(lineas):
            m = CABECERA.match(ln)
            if not m:
                continue
            if m.group(2).strip():
                lineas[i] = ln[:m.start(2)] + self._reemplazar_nombre(m.group(2), cuenta, "cabecera")
            else:
                j = next((k for k in range(i + 1, min(i + 3, len(lineas))) if lineas[k].strip()), None)
                if j is not None:
                    lineas[j] = self._reemplazar_nombre(lineas[j], cuenta, "cabecera")
        return "\n".join(lineas)

    def _sellos(self, t: str, cuenta: dict[str, int]) -> str:
        """Sello de firma digital (nombre + fecha y hora) y «Firmado digitalmente por: NOMBRE»."""
        t = SELLO.sub(lambda m: self._reemplazar_nombre(m.group(1), cuenta, "sello"), _separar_fecha(t))
        return FIRMADO_POR.sub(lambda m: m.group(1) + self._reemplazar_nombre(m.group(2), cuenta, "sello"), t)

    def _bloques_de_firma(self, t: str, cuenta: dict[str, int]) -> str:
        """Una línea que es solo un nombre, seguida de un cargo («Gerente General») o precedida de «Firmado
        digitalmente»."""
        lineas = t.split("\n")
        con_texto = [k for k, ln in enumerate(lineas) if ln.strip()]
        for pos, k in enumerate(con_texto):
            palabras = lineas[k].split()
            if not palabras or not all(_es_nombre(w) or w.lower() in PARTICULAS for w in palabras):
                continue
            sig = lineas[con_texto[pos + 1]] if pos + 1 < len(con_texto) else ""
            ant = lineas[con_texto[pos - 1]] if pos > 0 else ""
            if CARGO.match(sig) or re.search(r"(?i)firmado\s+digitalmente", ant):
                lineas[k] = self._reemplazar_nombre(lineas[k], cuenta, "firma")
        return "\n".join(lineas)

    def _firmantes(self, t: str, cuenta: dict[str, int]) -> str:
        """Después de «Regístrese…», las líneas que son solo un nombre (se miran hasta 8 líneas con texto)."""
        lineas = t.split("\n")
        for i, ln in enumerate(lineas):
            if not CIERRE.search(ln):
                continue
            vistas = 0
            for j in range(i + 1, len(lineas)):
                txt = lineas[j].strip()
                if not txt:
                    continue
                vistas += 1
                if vistas > 8 or re.search(r"\d", txt) or txt.upper().startswith("ANEXO"):
                    break
                palabras = txt.split()
                if all(_es_nombre(w) or w.lower() in PARTICULAS or w.upper() in NO_NOMBRES or "[PERSONA_" in w
                       for w in palabras):
                    lineas[j] = self._reemplazar_nombre(lineas[j], cuenta, "firmante")
        return "\n".join(lineas)

    def anonimizar(self, paginas: list[str]) -> Resultado:
        cuenta: dict[str, int] = {}
        res = []
        for p in paginas:
            t = self._privados(p, cuenta)
            t = self._tratamientos(t, cuenta)
            t = self._firmas_en_mayusculas(t, cuenta)
            t = self._cabeceras(t, cuenta)
            t = self._sellos(t, cuenta)
            t = self._firmantes(t, cuenta)
            t = self._bloques_de_firma(t, cuenta)
            t, k = DNI.subn("[DNI]", t); cuenta["dni"] = cuenta.get("dni", 0) + k
            t, k = CORREO.subn("[CORREO]", t); cuenta["correo"] = cuenta.get("correo", 0) + k
            t, k = TELEFONO.subn("[TELÉFONO]", t); cuenta["telefono"] = cuenta.get("telefono", 0) + k
            res.append(t)
        texto = plano(" ".join(res))
        pendientes = [n for n in self.privados if plano(n) in texto]
        restos = sum(restos_de_firma(p) for p in res)
        return Resultado(paginas=res, reemplazos={k: v for k, v in cuenta.items() if v}, pendientes=pendientes,
                         restos=restos)


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
