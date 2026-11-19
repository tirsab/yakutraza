"""Modo MVP: los hallazgos de calidad se guardan por alcance («muestra» = 20 EPS, «mvp» = EPS de MVP_EPS).

La migración inicial crea las tablas desde los metadatos actuales: en una base nueva la columna ya existe y aquí no se
hace nada.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("calidad_hallazgos")}
    if "alcance" not in cols:
        op.add_column("calidad_hallazgos", sa.Column("alcance", sa.String(10), nullable=False,
                                                     server_default="muestra"))
        op.create_index("ix_calidad_hallazgos_alcance", "calidad_hallazgos", ["alcance"])


def downgrade() -> None:
    op.drop_index("ix_calidad_hallazgos_alcance", table_name="calidad_hallazgos")
    op.drop_column("calidad_hallazgos", "alcance")
