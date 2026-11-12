"""Pasos de cada procedimiento (rules/pasos_procedimiento.yaml): supuesto de presentación."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.plazos.motor import Expediente


@lru_cache
def catalogo(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def pasos_de(exp: Expediente, cat: dict[str, Any], corte: date) -> dict[str, Any] | None:
    """Paso actual a la fecha de corte: el último paso con un hito ya iniciado."""
    lista = cat["procedimientos"].get(exp.tipo)
    if not lista:
        return None
    indice = {h: i for i, p in enumerate(lista) for h in p["hitos"]}
    iniciados = [indice[h.hito] for h in exp.hitos
                 if h.hito in indice and h.fecha_inicio is not None and h.fecha_inicio <= corte]
    terminado = exp.fecha_conclusion is not None and exp.fecha_conclusion <= corte
    actual = len(lista) - 1 if terminado else (max(iniciados) if iniciados else 0)
    return {"pasos": [{"clave": p["clave"], "nombre": p["nombre"]} for p in lista], "actual": actual,
            "n": len(lista), "terminado": terminado, "estado_validacion": cat.get("estado_validacion"),
            "fuente": cat.get("fuente")}


def por_paso(exps: list[Expediente], cat: dict[str, Any], corte: date) -> dict[str, Any]:
    """Cuántos expedientes hay en cada paso, por tipo de procedimiento."""
    res: dict[str, Any] = {}
    for e in exps:
        p = pasos_de(e, cat, corte)
        if p is None:
            continue
        g = res.setdefault(e.tipo, {"pasos": [{**x, "n": 0, "ids": []} for x in p["pasos"]], "total": 0})
        g["pasos"][p["actual"]]["n"] += 1
        g["pasos"][p["actual"]]["ids"].append(e.id)
        g["total"] += 1
    return res
