"""Catálogo de reglas de plazo (rules/plazos.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

TIPOS_RELOJ = ("normativo", "interno", "oficio")
RESPALDOS = ("norma_leida", "diccionario_y_flujograma", "solo_diccionario", "solo_flujograma",
             "supuesto_simulacion", "derivado_muestra")


@dataclass(frozen=True)
class ReglaPlazo:
    id: str
    procedimientos: tuple[str, ...]
    tipo_reloj: str
    respaldo: str
    estado_validacion: str
    fuentes: tuple[dict[str, str], ...]
    plazo_dh: int | None = None
    plazo_dias_calendario: int | None = None
    etapa: str | None = None
    hito: str | None = None
    hitos: tuple[str, ...] = ()
    regla: str | None = None
    inicio_conteo: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    discrepancia: dict[str, str] | None = None
    pregunta_dre: str | None = None
    nota: str | None = None
    activa: bool = True
    # Versiones de una misma regla comparten `familia` y se distinguen por vigencia.
    familia: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def aplica_a(self, procedimiento: str) -> bool:
        return "todos" in self.procedimientos or procedimiento in self.procedimientos

    def vigente_en(self, d: date) -> bool:
        """Sin vigencia verificada se asume aplicable, pero la regla sigue «por validar»."""
        if self.vigente_desde and d < self.vigente_desde:
            return False
        if self.vigente_hasta and d > self.vigente_hasta:
            return False
        return True

    @property
    def es_supuesto(self) -> bool:
        return self.respaldo == "supuesto_simulacion"

    def fuente_texto(self, documentos: dict[str, dict[str, str]]) -> str:
        """Fuentes legibles: «RGT, art. 93.8; Flujograma ... (encabezado)»."""
        partes = []
        for f in self.fuentes:
            doc = documentos.get(f["doc"], {}).get("titulo", f["doc"])
            corto = doc.split(" (")[0].split(",")[0] if f["doc"] not in ("RGT", "TUO_27444") else (
                "RGT (RCD 028-2021-SUNASS-CD)" if f["doc"] == "RGT" else "TUO Ley 27444 (DS 004-2019-JUS)")
            partes.append(f"{corto}, {f['ubicacion']}" if f.get("ubicacion") else corto)
        return "; ".join(partes)


class CatalogoPlazos:
    def __init__(self, datos: dict[str, Any]):
        self.documentos: dict[str, dict[str, str]] = datos.get("fuentes_documentales", {})
        self.umbral_por_vencer = int(datos["umbral_por_vencer_dh"]["valor"])
        self.reglas: dict[str, ReglaPlazo] = {}
        for r in datos["reglas"]:
            if r["id"] in self.reglas:
                raise ValueError(f"Regla de plazo repetida: {r['id']}")
            if r["tipo_reloj"] not in TIPOS_RELOJ:
                raise ValueError(f"tipo_reloj inválido en {r['id']}")
            if r["respaldo"] not in RESPALDOS:
                raise ValueError(f"respaldo inválido en {r['id']}")
            if r["estado_validacion"] not in ("validada", "por validar"):
                raise ValueError(f"estado_validacion inválido en {r['id']}")
            for f in r.get("fuentes", []):
                if f["doc"] not in self.documentos:
                    raise ValueError(f"{r['id']} cita un documento no declarado: {f['doc']}")
            proc = r["procedimiento"]
            conocidos = {"id", "procedimiento", "tipo_reloj", "respaldo", "estado_validacion", "fuentes",
                         "plazo_dh", "plazo_dias_calendario", "etapa", "hito", "hitos", "regla",
                         "inicio_conteo", "vigente_desde", "vigente_hasta", "discrepancia", "pregunta_dre",
                         "nota", "activa", "familia"}
            self.reglas[r["id"]] = ReglaPlazo(
                id=r["id"], procedimientos=tuple(proc if isinstance(proc, list) else [proc]),
                tipo_reloj=r["tipo_reloj"], respaldo=r["respaldo"], estado_validacion=r["estado_validacion"],
                fuentes=tuple(r.get("fuentes", [])), plazo_dh=r.get("plazo_dh"),
                plazo_dias_calendario=r.get("plazo_dias_calendario"), etapa=r.get("etapa"), hito=r.get("hito"),
                hitos=tuple(r.get("hitos") or ()), regla=r.get("regla"), inicio_conteo=r.get("inicio_conteo"),
                vigente_desde=r.get("vigente_desde"), vigente_hasta=r.get("vigente_hasta"),
                discrepancia=r.get("discrepancia"), pregunta_dre=r.get("pregunta_dre"), nota=r.get("nota"),
                activa=r.get("activa", True), familia=r.get("familia", r["id"]), extra={k: v for k, v in r.items() if k not in conocidos},
            )
        self._validar_versiones()

    def _validar_versiones(self) -> None:
        """Dos versiones activas de la misma familia no pueden estar vigentes a la vez."""
        familias: dict[str, list[ReglaPlazo]] = {}
        for r in self.reglas.values():
            if r.activa:
                familias.setdefault(r.familia, []).append(r)
        for fam, rs in familias.items():
            rs = sorted(rs, key=lambda r: r.vigente_desde or date.min)
            for a, b in zip(rs, rs[1:]):
                if a.vigente_hasta is None or (b.vigente_desde is not None and a.vigente_hasta >= b.vigente_desde):
                    raise ValueError(f"Versiones superpuestas en {fam}: {a.id} y {b.id}")

    def _activas(self, procedimiento: str, tipo_reloj: str, fecha: date | None = None):
        return [r for r in self.reglas.values()
                if r.activa and r.tipo_reloj == tipo_reloj and r.aplica_a(procedimiento)
                and (fecha is None or r.vigente_en(fecha))]

    @staticmethod
    def _mas_reciente(reglas: list[ReglaPlazo]) -> ReglaPlazo | None:
        """Entre versiones vigentes, la de vigente_desde más reciente (sin fecha = la más antigua)."""
        if not reglas:
            return None
        return max(reglas, key=lambda r: r.vigente_desde or date.min)

    def normativa(self, procedimiento: str, fecha: date | None = None) -> ReglaPlazo | None:
        """Plazo máximo del procedimiento completo (sin etapa ni hito)."""
        return self._mas_reciente([r for r in self._activas(procedimiento, "normativo", fecha)
                                   if "todos" not in r.procedimientos and r.etapa is None and r.hito is None
                                   and (r.plazo_dh or r.plazo_dias_calendario)])

    def etapas(self, procedimiento: str, fecha: date | None = None) -> dict[str, ReglaPlazo]:
        """Reglas por etapa; con `fecha`, la versión vigente en esa fecha."""
        res: dict[str, list[ReglaPlazo]] = {}
        for r in self._activas(procedimiento, "normativo", fecha):
            if r.etapa and r.hito is None:
                res.setdefault(r.etapa, []).append(r)
        return {e: self._mas_reciente(rs) for e, rs in res.items()}

    def etapa(self, procedimiento: str, etapa: str, fecha: date | None) -> ReglaPlazo | None:
        return self.etapas(procedimiento, fecha).get(etapa)

    def normativa_de_hito(self, procedimiento: str, hito: str, fecha: date | None = None) -> ReglaPlazo | None:
        """Plazo que la norma fija a un hito (por ejemplo, audiencia o comentarios), según la versión vigente."""
        return self._mas_reciente([r for r in self._activas(procedimiento, "normativo", fecha)
                                   if r.hito == hito and r.plazo_dh])

    def hitos_con_norma(self, procedimiento: str) -> set[str]:
        return {r.hito for r in self._activas(procedimiento, "normativo") if r.hito}

    def interna(self, procedimiento: str, hito: str, fecha: date | None = None) -> ReglaPlazo | None:
        return self._mas_reciente([r for r in self._activas(procedimiento, "interno", fecha) if r.hito == hito])

    def bloques(self, procedimiento: str) -> list[ReglaPlazo]:
        return [r for r in self._activas(procedimiento, "interno") if r.hitos]

    def de_oficio(self, procedimiento: str, hito: str, fecha: date | None = None) -> ReglaPlazo | None:
        return self._mas_reciente([r for r in self._activas(procedimiento, "oficio", fecha)
                                   if r.hito == hito and r.plazo_dh])

    def versiones(self, familia: str) -> list[ReglaPlazo]:
        return sorted((r for r in self.reglas.values() if r.familia == familia),
                      key=lambda r: r.vigente_desde or date.min)

    def transversal(self, regla_id: str) -> ReglaPlazo:
        return self.reglas[regla_id]


@lru_cache
def catalogo_desde(ruta: Path) -> CatalogoPlazos:
    return CatalogoPlazos(yaml.safe_load(Path(ruta).read_text(encoding="utf-8")))
