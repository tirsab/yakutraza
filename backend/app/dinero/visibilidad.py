"""Marca de visibilidad (público o reservado) de cada dato (rules/visibilidad.yaml)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PUBLICO, RESERVADO = "publico", "reservado"
# Campos de contexto que acompañan a cualquier dato público (no son datos en sí).
CONTEXTO = ("naturaleza",)


@lru_cache
def catalogo(ruta: Path) -> dict[str, Any]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    for entidad, campos in datos["entidades"].items():
        for campo, regla in campos.items():
            if regla["nivel"] not in (PUBLICO, RESERVADO):
                raise ValueError(f"Nivel inválido en {entidad}.{campo}: {regla['nivel']}")
    return datos


def mapa(cat: dict[str, Any], entidad: str) -> dict[str, str]:
    return {campo: regla["nivel"] for campo, regla in cat["entidades"][entidad].items()}


def nivel(cat: dict[str, Any], entidad: str, campo: str) -> str:
    """Un campo no catalogado es reservado (regla por defecto)."""
    regla = cat["entidades"].get(entidad, {}).get(campo)
    return regla["nivel"] if regla else cat.get("por_defecto", RESERVADO)


def solo_publico(cat: dict[str, Any], entidad: str, datos: dict[str, Any]) -> dict[str, Any]:
    """Devuelve solo los campos públicos de una entidad. La vista ciudadana (Fase 5) usará solo esto."""
    return {k: v for k, v in datos.items() if k in CONTEXTO or nivel(cat, entidad, k) == PUBLICO}
