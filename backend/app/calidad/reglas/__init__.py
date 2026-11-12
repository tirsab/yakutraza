"""Registro de reglas de calidad: id del catálogo YAML -> función."""

from __future__ import annotations

from collections.abc import Callable

from app.calidad.base import Contexto, Hallazgo, ReglaConfig
from app.ingesta.cargar import Muestra

FuncionRegla = Callable[[Muestra, ReglaConfig, Contexto], list[Hallazgo]]
REGISTRO: dict[str, FuncionRegla] = {}


def regla(regla_id: str):
    def decorador(f: FuncionRegla) -> FuncionRegla:
        if regla_id in REGISTRO:
            raise ValueError(f"Regla registrada dos veces: {regla_id}")
        REGISTRO[regla_id] = f
        return f
    return decorador


def cargar_modulos() -> None:
    # Importar los módulos registra sus reglas.
    from app.calidad.reglas import (  # noqa: F401
        aritmetica,
        duplicados,
        faltantes,
        fechas,
        formato,
        llaves,
        mef,
        plazos,
        unidades,
    )
