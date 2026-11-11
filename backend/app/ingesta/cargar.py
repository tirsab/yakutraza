"""Lectura de los CSV DS01-DS09 tal como llegan.

- Todo se lee como texto (así `ubigeo` conserva el cero inicial).
- Cada valor se convierte al tipo del diccionario; si no se puede, queda
  vacío en la columna tipada, se conserva en `valores_originales` y se anota
  un problema de formato (que el control de calidad convierte en hallazgo).
- No se elimina, corrige ni deduplica ninguna fila.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.ingesta.conversion import ErrorConversion, convertir
from app.ingesta.especificacion import DATASETS, Dataset

PRIMERA_FILA_DATOS = 2  # la línea 1 del CSV es el encabezado


@dataclass
class ProblemaFormato:
    dataset: str
    fila: int | None  # línea del CSV; None si afecta al archivo completo
    columna: str | None
    valor: str | None
    mensaje: str


@dataclass
class TablaCargada:
    spec: Dataset
    # Valores tipados (Decimal, int, date, bool, str o None) + columna `_fila`.
    datos: pd.DataFrame
    # Texto original de cada celda, mismo índice que `datos`.
    crudos: pd.DataFrame
    sha256: str


@dataclass
class Muestra:
    data_dir: Path
    tablas: dict[str, TablaCargada] = field(default_factory=dict)
    problemas: list[ProblemaFormato] = field(default_factory=list)

    def __getitem__(self, nombre: str) -> pd.DataFrame:
        return self.tablas[nombre].datos


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    h.update(ruta.read_bytes())
    return h.hexdigest()


def cargar_tabla(ruta: Path, spec: Dataset, problemas: list[ProblemaFormato]) -> TablaCargada:
    with ruta.open(encoding="utf-8", newline="") as f:
        lector = csv.reader(f)
        encabezado = next(lector)
        filas = list(lector)

    esperadas = [c.nombre for c in spec.columnas]
    faltan = [c for c in esperadas if c not in encabezado]
    sobran = [c for c in encabezado if c not in esperadas]
    if faltan or sobran:
        problemas.append(ProblemaFormato(
            spec.nombre, None, None, None,
            f"Las columnas del CSV no coinciden con la hoja {spec.nombre} del diccionario. "
            f"Faltan: {faltan or 'ninguna'}. Sobran: {sobran or 'ninguna'}.",
        ))

    crudos = pd.DataFrame(filas, columns=encabezado, dtype=str)
    for c in faltan:
        crudos[c] = ""
    crudos.index = range(PRIMERA_FILA_DATOS, PRIMERA_FILA_DATOS + len(crudos))

    tipados: dict[str, list] = {}
    for col in spec.columnas:
        valores = []
        for fila, v in crudos[col.nombre].items():
            try:
                valores.append(convertir(v, col.tipo))
            except ErrorConversion as e:
                problemas.append(ProblemaFormato(spec.nombre, int(fila), col.nombre, v, str(e)))
                valores.append(None)
        tipados[col.nombre] = valores
    datos = pd.DataFrame(tipados, index=crudos.index, dtype=object)
    datos["_fila"] = crudos.index
    return TablaCargada(spec, datos, crudos, _sha256(ruta))


def cargar_muestra(data_dir: Path) -> Muestra:
    data_dir = Path(data_dir)
    muestra = Muestra(data_dir)
    for spec in DATASETS:
        ruta = data_dir / spec.archivo
        if not ruta.exists():
            muestra.problemas.append(ProblemaFormato(
                spec.nombre, None, None, None, f"No se encontró {spec.archivo} en DATA_DIR ({data_dir})."
            ))
            continue
        muestra.tablas[spec.nombre] = cargar_tabla(ruta, spec, muestra.problemas)
    return muestra
