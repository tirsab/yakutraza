"""Tipos comunes del control de calidad: catálogo de reglas y hallazgos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

SEVERIDADES = ("alta", "media", "baja", "informativa")

# Tipos de problema que la hoja Léame y la hoja Relaciones del diccionario
# anuncian en la muestra. El reporte indica, para cada uno, si se encontró.
TIPOS_ANUNCIADOS: dict[str, str] = {
    "duplicado": "Duplicados (hoja Léame)",
    "unidad_sospechosa": "Montos en otra unidad (hoja Léame)",
    "llave_sin_cruce": "Códigos que no cruzan (hoja Léame)",
    "reporte_faltante": "Reportes faltantes (hoja Léame)",
    "fecha_inconsistente": "Fechas inconsistentes (hoja Léame)",
    "diferencia_mef": "Diferencias con el MEF (hoja Léame)",
    "cui_sin_mef": "CUI declarado en DS03 que no figura en DS08 (hoja Relaciones)",
}

ETIQUETA_TIPO: dict[str, str] = {
    **{k: v.split(" (")[0] for k, v in TIPOS_ANUNCIADOS.items()},
    "formato": "Formato y esquema",
    "dato_no_registrado": "Dato no registrado",
    "coherencia_aritmetica": "Coherencia aritmética",
    "desfase_mef": "Diferencias con el MEF explicadas o no verificables por el desfase de fechas",
}


@dataclass(frozen=True)
class ReglaConfig:
    id: str
    tipo: str
    titulo: str
    descripcion: str
    severidad: str
    fuente: str
    estado_validacion: str
    activa: bool
    parametros: dict[str, Any]

    def param(self, nombre: str, defecto: Any = None) -> Any:
        p = self.parametros.get(nombre)
        if p is None:
            return defecto
        return p.get("valor", defecto) if isinstance(p, dict) else p


@dataclass
class Hallazgo:
    regla_id: str
    tipo: str
    severidad: str
    dataset: str
    fila: int | None
    llave: str | None
    titulo: str
    explicacion: str
    fuente_regla: str
    estado_validacion: str
    valor_observado: str | None = None
    valor_esperado: str | None = None
    detalle: dict[str, Any] | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "regla_id": self.regla_id,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "dataset": self.dataset,
            "fila": self.fila,
            "llave": self.llave,
            "titulo": self.titulo,
            "explicacion": self.explicacion,
            "fuente_regla": self.fuente_regla,
            "estado_validacion": self.estado_validacion,
            "valor_observado": self.valor_observado,
            "valor_esperado": self.valor_esperado,
            "detalle": self.detalle,
        }


@dataclass
class Contexto:
    fecha_corte: date
    reglas: dict[str, ReglaConfig] = field(default_factory=dict)


def nuevo(cfg: ReglaConfig, dataset: str, fila: int | None, llave: str | None, explicacion: str,
          *, observado: Any = None, esperado: Any = None, severidad: str | None = None,
          titulo: str | None = None, detalle: dict[str, Any] | None = None, tipo: str | None = None) -> Hallazgo:
    """Crea un hallazgo con la fuente y el estado de validación de su regla."""
    sev = severidad or cfg.severidad
    assert sev in SEVERIDADES, sev
    return Hallazgo(
        regla_id=cfg.id, tipo=tipo or cfg.tipo, severidad=sev, dataset=dataset,
        fila=int(fila) if fila is not None else None, llave=llave,
        titulo=titulo or cfg.titulo, explicacion=explicacion,
        fuente_regla=cfg.fuente, estado_validacion=cfg.estado_validacion,
        valor_observado=_texto(observado), valor_esperado=_texto(esperado), detalle=detalle,
    )


def _texto(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def cargar_catalogo(ruta: Path) -> dict[str, ReglaConfig]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    reglas: dict[str, ReglaConfig] = {}
    for r in datos["reglas"]:
        if r["id"] in reglas:
            raise ValueError(f"Regla repetida en el catálogo: {r['id']}")
        if r["severidad"] not in SEVERIDADES:
            raise ValueError(f"Severidad inválida en {r['id']}: {r['severidad']}")
        if r["estado_validacion"] not in ("validada", "por validar"):
            raise ValueError(f"estado_validacion inválido en {r['id']}")
        reglas[r["id"]] = ReglaConfig(
            id=r["id"], tipo=r["tipo"], titulo=r["titulo"], descripcion=r.get("descripcion", "").strip(),
            severidad=r["severidad"], fuente=r["fuente"], estado_validacion=r["estado_validacion"],
            activa=bool(r.get("activa", True)), parametros=r.get("parametros") or {},
        )
    return reglas
