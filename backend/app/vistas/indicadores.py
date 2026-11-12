"""docs/indicadores.md: línea base de la muestra, con la misma función que alimenta el tablero."""

from __future__ import annotations

from typing import Any

from app.vistas.etiquetas import etiqueta
from app.vistas.tablero import Contexto, supera_plazo


def _pct(g: dict[str, Any]) -> str:
    return "no calculable" if g["porcentaje"] is None else f"{g['porcentaje']:.1f} %".replace(".", ",")


def _tabla(grupos: dict[str, dict[str, Any]], nombre: str, cat: dict[str, Any] | None) -> list[str]:
    filas = [f"| {nombre} | Superan el plazo | Con datos | % | No calculables |", "|---|---:|---:|---:|---:|"]
    for k, g in sorted(grupos.items()):
        etq = etiqueta(cat, "tipo_procedimiento", k) if cat else k
        filas.append(f"| {etq} | {g['superan']} | {g['calculables']} | {_pct(g)} | {g['no_calculables']} |")
    return filas


def markdown(ctx: Contexto, cat: dict[str, Any]) -> str:
    sp = supera_plazo(ctx)
    t = sp["total"]
    lineas = [
        "# Indicadores de línea base · muestra simulada",
        "",
        "> **Muestra simulada.** Datos sintéticos de la muestra del Hackathon Sunass «Lideresas por el Agua». "
        "No describen a ninguna EPS real ni el desempeño real de la Sunass.",
        "",
        f"Generado con `python -m app.cli indicadores`, con la misma función que alimenta el tablero gerencial "
        f"(`app/vistas/tablero.py`, `supera_plazo`). Fecha de corte de la muestra: {sp['a_la_fecha']:%d-%m-%Y}.",
        "",
        "## Expedientes que superan el plazo máximo",
        "",
        f"- **Fórmula:** {sp['formula']}.",
        f"- **Resultado:** {t['superan']} de {t['calculables']} expedientes con datos ({_pct(t)}); "
        f"{t['en_tramite_superan']} de ellos siguen en trámite.",
        f"- **No calculables:** {t['no_calculables']} expedientes. DS02 no trae los días atribuibles a la Sunass o el "
        "plazo máximo (por ejemplo, reportes periódicos y reajustes por IPM). No se estiman.",
        f"- **Nota:** {sp['nota']}",
        "",
        "### Por tipo de trámite",
        "",
        *_tabla(sp["por_tipo"], "Tipo de trámite", cat),
        "",
        "### Por EPS",
        "",
        *_tabla({k: v for k, v in sp["por_eps"].items() if v["calculables"] or v["no_calculables"]}, "EPS", None),
        "",
        "## Expedientes que superan el plazo",
        "",
        ", ".join(f"`{i}`" for i in sorted(t["ids_superan"])) or "Ninguno.",
        "",
        f"Fuente: {sp['fuente']}.",
        "",
    ]
    return "\n".join(lineas)
