"""Etiquetas en lenguaje claro para los códigos de la muestra (rules/etiquetas.yaml)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache
def catalogo(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def etiqueta(cat: dict[str, Any], categoria: str, codigo: Any) -> str:
    """Etiqueta del código; si falta, el código sin guiones bajos (nunca se muestra crudo)."""
    if codigo is None:
        return "—"
    valor = cat["categorias"].get(categoria, {}).get(str(codigo))
    return valor if valor else str(codigo).replace("_", " ")
