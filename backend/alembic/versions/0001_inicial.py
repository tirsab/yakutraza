"""Esquema inicial (Fase 1): tablas DS01-DS09, carga_lotes y calidad_hallazgos.

Las tablas de datos se generan desde la especificación de app.ingesta.especificacion,
que a su vez se verifica contra el diccionario de variables. Las fases siguientes
agregan migraciones incrementales.

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""
from alembic import op

from app.db import metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(op.get_bind())


def downgrade() -> None:
    metadata.drop_all(op.get_bind())
