"""Usuarios ficticios de demostración (rules/usuarios_demo.yaml) y roles (rules/roles.yaml)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROLES_SUNASS = ("especialista_srt", "coordinacion_srt", "direccion_dre", "otras_areas")
PATRON_EPS = re.compile(r"^eps-(EPS\d{2})$")


@dataclass(frozen=True)
class Usuario:
    id: str
    nombre: str
    rol: str
    unidad: str
    permisos: tuple[str, ...] = field(default_factory=tuple)
    cod_eps: str | None = None
    vistas: tuple[str, ...] = field(default_factory=tuple)
    alcance: str = "todas"
    inicio: str = "/"

    def puede(self, permiso: str) -> bool:
        return permiso in self.permisos

    def ve(self, vista: str) -> bool:
        return vista in self.vistas

    @property
    def es_sunass(self) -> bool:
        return self.rol in ROLES_SUNASS

    @property
    def es_ciudadania(self) -> bool:
        return self.rol == "ciudadania"

    def como_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "permisos": list(self.permisos), "vistas": list(self.vistas),
                "rotulo": "Usuario ficticio de demostración"}


class ErrorPermiso(PermissionError):
    pass


@lru_cache
def roles_desde(ruta: Path) -> dict[str, dict[str, Any]]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))["roles"]


def _crear(roles: dict[str, dict[str, Any]], id: str, nombre: str, rol: str, unidad: str,
           cod_eps: str | None = None) -> Usuario:
    r = roles[rol]
    return Usuario(id=id, nombre=nombre, rol=rol, unidad=unidad, permisos=tuple(r.get("acciones") or ()),
                   cod_eps=cod_eps, vistas=tuple(r.get("vistas") or ()), alcance=r.get("alcance", "todas"),
                   inicio=r.get("inicio", "/"))


@lru_cache
def _yaml(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


@lru_cache
def usuarios_desde(ruta: Path) -> dict[str, Usuario]:
    """Usuarios fijos del YAML. Los permisos y vistas salen del rol (roles.yaml, en la misma carpeta)."""
    roles = roles_desde(Path(ruta).parent / "roles.yaml")
    return {u["id"]: _crear(roles, u["id"], u["nombre"], u["rol"], u["unidad"], u.get("cod_eps"))
            for u in _yaml(ruta)["usuarios"]}


def usuario_eps(ruta: Path, cod_eps: str) -> Usuario:
    p = _yaml(ruta)["plantilla_eps"]
    roles = roles_desde(Path(ruta).parent / "roles.yaml")
    return _crear(roles, p["id"].format(cod_eps=cod_eps), p["nombre"].format(cod_eps=cod_eps), p["rol"],
                  p["unidad"], cod_eps)


def ciudadania(ruta: Path) -> Usuario:
    roles = roles_desde(Path(ruta).parent / "roles.yaml")
    return _crear(roles, "ciudadania", "Ciudadanía (sin sesión)", "ciudadania", "Público")


def resolver(ruta: Path, id_usuario: str | None) -> Usuario | None:
    """Usuario fijo, usuario de EPS («eps-EPS02») o None si no existe."""
    if not id_usuario:
        return None
    fijo = usuarios_desde(ruta).get(id_usuario)
    if fijo is not None:
        return fijo
    m = PATRON_EPS.match(id_usuario)
    return usuario_eps(ruta, m.group(1)) if m else None


def exigir(usuario: Usuario | None, permiso: str, cod_eps: str | None = None) -> Usuario:
    if usuario is None or usuario.es_ciudadania:
        raise ErrorPermiso("Falta identificar al usuario (encabezado X-Usuario).")
    if not usuario.puede(permiso):
        raise ErrorPermiso(f"El rol {usuario.rol} no tiene el permiso «{permiso}».")
    if usuario.cod_eps and cod_eps and usuario.cod_eps != cod_eps:
        raise ErrorPermiso(f"El usuario de {usuario.cod_eps} no puede actuar sobre expedientes de {cod_eps}.")
    return usuario
