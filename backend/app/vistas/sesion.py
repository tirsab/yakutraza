"""Sesión de la demo: quién mira (encabezado X-Usuario) y qué vistas puede leer (rules/roles.yaml)."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.expediente.usuarios import Usuario, ciudadania, resolver


def ruta_usuarios(s: Settings) -> Path:
    return Path(s.rules_dir) / "usuarios_demo.yaml"


def sesion(x_usuario: str | None = Header(None), s: Settings = Depends(get_settings)) -> Usuario:
    """Usuario de la petición. Sin encabezado, o con MODO_DEMO=false, es ciudadanía."""
    if not s.modo_demo or not x_usuario:
        return ciudadania(ruta_usuarios(s))
    u = resolver(ruta_usuarios(s), x_usuario)
    if u is None:
        raise HTTPException(401, f"Usuario de demostración desconocido: {x_usuario}")
    return u


def exige_vista(vista: str):
    """Dependencia: la vista debe estar permitida para el rol del usuario."""
    def _dep(u: Usuario = Depends(sesion)) -> Usuario:
        if not u.ve(vista):
            raise HTTPException(401 if u.es_ciudadania else 403,
                                f"La vista «{vista}» no está disponible para el rol {u.rol}.")
        return u
    return _dep


def alcance_eps(u: Usuario, cod_eps: str | None) -> str | None:
    """Filtro de EPS efectivo: una EPS solo ve su cod_eps; pedir otra es un error 403."""
    if u.alcance != "propia_eps":
        return cod_eps
    if cod_eps and cod_eps != u.cod_eps:
        raise HTTPException(403, f"El usuario de {u.cod_eps} solo puede ver datos de {u.cod_eps}.")
    return u.cod_eps
