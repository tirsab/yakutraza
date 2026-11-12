"""Usuarios ficticios de demostración (rules/usuarios_demo.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROLES_SUNASS = ("especialista_srt", "coordinacion_srt", "direccion_dre", "otras_areas")


@dataclass(frozen=True)
class Usuario:
    id: str
    nombre: str
    rol: str
    unidad: str
    permisos: tuple[str, ...] = field(default_factory=tuple)
    cod_eps: str | None = None

    def puede(self, permiso: str) -> bool:
        return permiso in self.permisos

    @property
    def es_sunass(self) -> bool:
        return self.rol in ROLES_SUNASS


class ErrorPermiso(PermissionError):
    pass


@lru_cache
def usuarios_desde(ruta: Path) -> dict[str, Usuario]:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    return {
        u["id"]: Usuario(id=u["id"], nombre=u["nombre"], rol=u["rol"], unidad=u["unidad"],
                         permisos=tuple(u.get("permisos") or ()), cod_eps=u.get("cod_eps"))
        for u in datos["usuarios"]
    }


def exigir(usuario: Usuario | None, permiso: str, cod_eps: str | None = None) -> Usuario:
    if usuario is None:
        raise ErrorPermiso("Falta identificar al usuario (encabezado X-Usuario).")
    if not usuario.puede(permiso):
        raise ErrorPermiso(f"El rol {usuario.rol} no tiene el permiso «{permiso}».")
    if usuario.cod_eps and cod_eps and usuario.cod_eps != cod_eps:
        raise ErrorPermiso(f"El usuario de {usuario.cod_eps} no puede actuar sobre expedientes de {cod_eps}.")
    return usuario
