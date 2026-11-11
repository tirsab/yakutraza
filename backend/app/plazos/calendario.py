"""Calendario de días hábiles (lunes a viernes, sin feriados nacionales).

Convención de conteo (ver rules/plazos.yaml, regla PLZ-COMPUTO): un plazo de
N días hábiles empieza a contarse el día hábil siguiente a la fecha de inicio
(TUO de la Ley 27444, art. 144.1; RGT art. 45.1). Con esta convención se
reproducen las 65 fechas límite de DS02 que tienen plazo máximo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import holidays
import yaml


@dataclass(frozen=True)
class Feriado:
    fecha: date
    nombre: str
    fuente: str


@dataclass(frozen=True)
class DiferenciaCalendario:
    fecha: date
    nombre: str
    en_libreria: bool
    en_supuestos: bool
    explicacion: str


class Calendario:
    def __init__(self, config: dict, desde: int = 2018, hasta: int = 2032):
        lib_cfg = config["libreria"]
        self.fuente_libreria = lib_cfg["fuente"]
        self.fuente_supuestos = config["fuente_feriados_con_vigencia"]
        self._config = config
        lib = holidays.country_holidays(lib_cfg["pais"], years=range(desde, hasta + 1))
        self._feriados: dict[date, Feriado] = {
            d: Feriado(d, n, self.fuente_libreria) for d, n in lib.items()
        }
        self._libreria = set(lib)
        # La hoja Supuestos manda: sus feriados con vigencia se agregan aunque la librería no los tenga.
        for f in config["feriados_con_vigencia"]:
            for anio in range(max(desde, f["desde"]), hasta + 1):
                d = date(anio, f["mes"], f["dia"])
                self._feriados.setdefault(d, Feriado(d, f["nombre"], self.fuente_supuestos))
        self._extras_supuestos = config["feriados_con_vigencia"]

    # ---------------------------------------------------------------- consulta
    def es_feriado(self, d: date) -> bool:
        return d in self._feriados

    def es_habil(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self._feriados

    def feriados(self, anio: int) -> list[Feriado]:
        return sorted((f for d, f in self._feriados.items() if d.year == anio), key=lambda f: f.fecha)

    # ---------------------------------------------------------------- cómputo
    def sumar_dias_habiles(self, inicio: date, n: int) -> date:
        """Fecha en que vence un plazo de `n` DH contado desde el día hábil siguiente a `inicio`."""
        if n < 0:
            raise ValueError("El plazo no puede ser negativo")
        d = inicio
        while n > 0:
            d += timedelta(days=1)
            if self.es_habil(d):
                n -= 1
        return d

    def dias_habiles_entre(self, desde: date, hasta: date) -> int:
        """Días hábiles en el intervalo (desde, hasta]: los que transcurren después de `desde`."""
        if hasta <= desde:
            return 0
        n, d = 0, desde
        while d < hasta:
            d += timedelta(days=1)
            if self.es_habil(d):
                n += 1
        return n

    def siguiente_habil(self, d: date) -> date:
        """`d` si es hábil; si no, el primer día hábil siguiente (TUO Ley 27444, art. 145.2)."""
        while not self.es_habil(d):
            d += timedelta(days=1)
        return d

    # ------------------------------------------------------------ diferencias
    def diferencias_con_supuestos(self) -> list[DiferenciaCalendario]:
        """Compara, año por año, los feriados con vigencia de la hoja Supuestos con la librería."""
        rango = self._config["anios_verificados"]
        res = []
        for f in self._extras_supuestos:
            for anio in range(rango["desde"], rango["hasta"] + 1):
                d = date(anio, f["mes"], f["dia"])
                en_sup = anio >= f["desde"]
                en_lib = d in self._libreria
                if en_sup != en_lib:
                    res.append(DiferenciaCalendario(
                        d, f["nombre"], en_lib, en_sup,
                        f"{d}: la hoja Supuestos {'lo considera' if en_sup else 'no lo considera'} feriado "
                        f"(vigente desde {f['desde']}) y la librería {'sí' if en_lib else 'no'}. "
                        "Validar con el calendario oficial.",
                    ))
        return res


@lru_cache
def calendario_desde(ruta: Path) -> Calendario:
    return Calendario(yaml.safe_load(Path(ruta).read_text(encoding="utf-8")))
