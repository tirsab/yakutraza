"""Verificación de la especificación contra diccionario_variables.xlsx.

Compara, para cada hoja de dataset, el nombre, el tipo y la unidad de cada
variable. No modifica nada: devuelve las diferencias para que se reporten.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from app.ingesta.cargar import ProblemaFormato
from app.ingesta.especificacion import DATASETS

ARCHIVO_DICCIONARIO = "diccionario_variables.xlsx"


def leer_variables(ruta: Path) -> dict[str, list[tuple[str, str, str]]]:
    """Hoja -> [(variable, tipo, unidad)] según el diccionario."""
    wb = load_workbook(ruta, read_only=True, data_only=True)
    try:
        resultado: dict[str, list[tuple[str, str, str]]] = {}
        for ws in wb.worksheets:
            filas = list(ws.iter_rows(values_only=True))
            inicio = next((i for i, f in enumerate(filas) if f and f[0] == "Variable"), None)
            if inicio is None:
                continue  # hojas Léame, Relaciones, Hitos, Supuestos
            resultado[ws.title] = [
                (str(f[0]), str(f[2]), str(f[3])) for f in filas[inicio + 1:] if f and f[0]
            ]
        return resultado
    finally:
        wb.close()


def verificar_contra_diccionario(data_dir: Path) -> list[ProblemaFormato]:
    ruta = Path(data_dir) / ARCHIVO_DICCIONARIO
    if not ruta.exists():
        return [ProblemaFormato("diccionario", None, None, None,
                                f"No se encontró {ARCHIVO_DICCIONARIO}; no se pudo verificar la especificación.")]
    hojas = leer_variables(ruta)
    problemas: list[ProblemaFormato] = []
    for ds in DATASETS:
        if ds.nombre not in hojas:
            problemas.append(ProblemaFormato(ds.nombre, None, None, None,
                                             f"El diccionario no tiene la hoja {ds.nombre}."))
            continue
        dicc = {v: (t, u) for v, t, u in hojas[ds.nombre]}
        spec = {c.nombre: (c.tipo, c.unidad) for c in ds.columnas}
        for var in dicc.keys() - spec.keys():
            problemas.append(ProblemaFormato(ds.nombre, None, var, None,
                                             f"La variable {var} está en el diccionario pero no en la especificación."))
        for var in spec.keys() - dicc.keys():
            problemas.append(ProblemaFormato(ds.nombre, None, var, None,
                                             f"La variable {var} está en la especificación pero no en el diccionario."))
        for var in spec.keys() & dicc.keys():
            if spec[var] != dicc[var]:
                problemas.append(ProblemaFormato(
                    ds.nombre, None, var, None,
                    f"Tipo/unidad de {var}: especificación {spec[var]} vs diccionario {dicc[var]}.",
                ))
    return problemas
