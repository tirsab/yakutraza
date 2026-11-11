"""Reporte HTML descargable con todos los hallazgos de calidad."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from app.calidad.base import ETIQUETA_TIPO, SEVERIDADES, TIPOS_ANUNCIADOS, ReglaConfig

_ENV = Environment(loader=PackageLoader("app", "templates"), autoescape=select_autoescape(["html", "j2"]))

ICONO_SEVERIDAD = {"alta": "▲", "media": "◆", "baja": "▽", "informativa": "ℹ"}


def construir_html(hallazgos: list[dict[str, Any]], lote: dict[str, Any], catalogo: dict[str, ReglaConfig],
                   generado: datetime | None = None) -> str:
    por_tipo: dict[str, list[dict[str, Any]]] = {}
    for h in hallazgos:
        por_tipo.setdefault(h["tipo"], []).append(h)
    orden_tipos = list(TIPOS_ANUNCIADOS) + sorted(t for t in por_tipo if t not in TIPOS_ANUNCIADOS)
    conteo = Counter((h["tipo"], h["severidad"]) for h in hallazgos)
    anunciados = [
        {"tipo": t, "etiqueta": e, "n": len(por_tipo.get(t, []))} for t, e in TIPOS_ANUNCIADOS.items()
    ]
    return _ENV.get_template("reporte_calidad.html.j2").render(
        hallazgos=hallazgos,
        por_tipo=por_tipo,
        orden_tipos=[t for t in orden_tipos if t in por_tipo],
        conteo=conteo,
        severidades=SEVERIDADES,
        icono=ICONO_SEVERIDAD,
        etiqueta_tipo=ETIQUETA_TIPO,
        anunciados=anunciados,
        lote=lote,
        catalogo=list(catalogo.values()),
        generado=(generado or datetime.now()).strftime("%Y-%m-%d %H:%M"),
        total_por_severidad=Counter(h["severidad"] for h in hallazgos),
    )


def escribir_reporte(html: str, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "calidad.html"
    ruta.write_text(html, encoding="utf-8")
    return ruta
