"""Configuración leída de variables de entorno (o de un archivo .env)."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_REPO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(RAIZ_REPO / ".env"), extra="ignore")

    # Carpeta con los CSV y el diccionario. No se versiona (ver README).
    data_dir: Path = RAIZ_REPO / "data"
    # Catálogos de reglas en YAML.
    rules_dir: Path = RAIZ_REPO / "rules"
    # Casos reales: parte pública (versionada) y carpeta de la parte privada (no versionada).
    casos_reales_dir: Path = RAIZ_REPO / "casos_reales"
    casos_reales_privados_dir: Path | None = None  # por defecto, DATA_DIR/casos_reales
    # Carpeta donde se escribe el reporte HTML de calidad.
    reportes_dir: Path = RAIZ_REPO / "reportes"
    # "Hoy" para la demo: fecha de corte de la muestra (hoja Léame del diccionario).
    fecha_corte: date = date(2026, 9, 30)
    # Modo demo: muestra el selector «Ver como» y acepta el encabezado X-Usuario de los usuarios
    # ficticios. En un enlace público se desactiva con MODO_DEMO=false: toda persona es ciudadanía.
    modo_demo: bool = True
    # PostgreSQL 16 en Docker; SQLite solo para desarrollo y pruebas sin Docker.
    database_url: str = f"sqlite:///{(RAIZ_REPO / 'yakutraza_local.db').as_posix()}"


def dir_privado(s: "Settings") -> Path:
    return Path(s.casos_reales_privados_dir) if s.casos_reales_privados_dir else Path(s.data_dir) / "casos_reales"


@lru_cache
def get_settings() -> Settings:
    return Settings()
