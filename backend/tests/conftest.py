from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

import pytest

from app.calidad.base import cargar_catalogo
from app.calidad.motor import evaluar
from app.calidad.reglas import REGISTRO, cargar_modulos
from app.calidad.base import Contexto
from app.config import RAIZ_REPO, get_settings
from app.ingesta.cargar import cargar_muestra
from app.ingesta.especificacion import dataset

CATALOGO = get_settings().rules_dir / "calidad.yaml"
CORTE = date(2026, 9, 30)


def escribir_csvs(carpeta: Path, tablas: dict[str, list[dict[str, str]]]) -> Path:
    """Escribe CSV con todas las columnas de la especificación (las no dadas quedan vacías)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, filas in tablas.items():
        cols = [c.nombre for c in dataset(nombre).columnas]
        with (carpeta / f"{nombre}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for fila in filas:
                w.writerow({c: fila.get(c, "") for c in cols})
    return carpeta


@pytest.fixture
def muestra_de(tmp_path):
    def _crear(tablas):
        return cargar_muestra(escribir_csvs(tmp_path / "data", tablas))
    return _crear


@pytest.fixture(scope="session")
def catalogo():
    return cargar_catalogo(CATALOGO)


@pytest.fixture
def correr(catalogo):
    """Ejecuta una sola regla del catálogo sobre una muestra."""
    cargar_modulos()

    def _correr(regla_id, muestra, corte=CORTE):
        return REGISTRO[regla_id](muestra, catalogo[regla_id], Contexto(fecha_corte=corte, reglas=catalogo))
    return _correr


def _data_dir_real() -> Path | None:
    candidatos = [os.environ.get("DATA_DIR"), str(get_settings().data_dir)]
    if len(RAIZ_REPO.parents) >= 3:  # worktree en <repo>/.claude/worktrees/<nombre>
        candidatos.append(str(RAIZ_REPO.parents[2] / "data"))
    for c in candidatos:
        if c and (Path(c) / "ds02_procedimientos.csv").exists():
            return Path(c)
    return None


@pytest.fixture(scope="session")
def data_dir_real():
    d = _data_dir_real()
    if d is None:
        pytest.skip("No se encontraron los CSV de la muestra (define DATA_DIR).")
    return d


@pytest.fixture(scope="session")
def muestra_real(data_dir_real):
    return cargar_muestra(data_dir_real)


@pytest.fixture(scope="session")
def hallazgos_reales(muestra_real):
    return evaluar(muestra_real, CATALOGO, CORTE)
