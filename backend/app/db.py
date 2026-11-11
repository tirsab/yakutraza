"""Esquema de base de datos y conexión.

Las tablas de datos se generan a partir de la especificación (una por CSV),
con los tipos del diccionario. Cada fila guarda `fila_origen` (número de línea
del CSV, encabezado = línea 1) y `valores_originales` (texto tal como llegó),
para poder citar dataset y fila en cada alerta.

Funciona con PostgreSQL 16 (Docker) y con SQLite (solo desarrollo y pruebas).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine

from app.config import get_settings
from app.ingesta.especificacion import DATASETS

metadata = MetaData()

_TIPO_SQL = {
    "texto": lambda: Text(),
    "entero": lambda: BigInteger(),
    # Sin escala fija: no se redondea en silencio al cargar.
    "decimal": lambda: Numeric(24, 6),
    "fecha": lambda: Date(),
    "booleano": lambda: Boolean(),
}

carga_lotes = Table(
    "carga_lotes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("iniciado", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("data_dir", Text, nullable=False),
    Column("fecha_corte", Date, nullable=False),
    Column("archivos", JSON, nullable=False),  # nombre -> {filas, sha256}
    Column("estado", String(20), nullable=False),
)

calidad_hallazgos = Table(
    "calidad_hallazgos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("lote_id", Integer, ForeignKey("carga_lotes.id"), nullable=False, index=True),
    Column("dataset", String(60), nullable=False, index=True),
    # Línea del CSV (encabezado = 1). Vacío si el hallazgo agrupa varias filas
    # (sus líneas quedan en detalle["filas"]).
    Column("fila", Integer),
    Column("llave", Text),
    Column("regla_id", String(20), nullable=False, index=True),
    Column("tipo", String(40), nullable=False, index=True),
    Column("severidad", String(15), nullable=False, index=True),
    Column("titulo", Text, nullable=False),
    Column("explicacion", Text, nullable=False),
    Column("valor_observado", Text),
    Column("valor_esperado", Text),
    Column("fuente_regla", Text, nullable=False),
    Column("estado_validacion", String(20), nullable=False),
    Column("detalle", JSON),
    Column("creado", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def _tabla_dataset(ds) -> Table:
    cols = [
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("lote_id", Integer, ForeignKey("carga_lotes.id"), nullable=False),
        Column("fila_origen", Integer, nullable=False),
    ]
    cols += [Column(c.nombre, _TIPO_SQL[c.tipo]()) for c in ds.columnas]
    cols.append(Column("valores_originales", JSON, nullable=False))
    t = Table(ds.tabla, metadata, *cols)
    # Índice (no único) por la llave natural: la muestra trae duplicados a propósito.
    Index(f"ix_{ds.tabla}_llave", *[t.c[k] for k in ds.llave])
    return t


TABLAS_DATASETS: dict[str, Table] = {ds.nombre: _tabla_dataset(ds) for ds in DATASETS}


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, future=True)


RUTA_ALEMBIC = Path(__file__).resolve().parents[1] / "alembic.ini"


def crear_esquema(engine: Engine) -> None:
    """Aplica las migraciones de Alembic hasta la última versión."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(RUTA_ALEMBIC))
    with engine.begin() as cx:
        cfg.attributes["connection"] = cx
        command.upgrade(cfg, "head")
