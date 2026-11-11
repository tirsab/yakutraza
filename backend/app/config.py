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
    # Carpeta donde se escribe el reporte HTML de calidad.
    reportes_dir: Path = RAIZ_REPO / "reportes"
    # "Hoy" para la demo: fecha de corte de la muestra (hoja Léame del diccionario).
    fecha_corte: date = date(2026, 9, 30)
    # PostgreSQL 16 en Docker; SQLite solo para desarrollo y pruebas sin Docker.
    database_url: str = f"sqlite:///{(RAIZ_REPO / 'yakutraza_local.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
