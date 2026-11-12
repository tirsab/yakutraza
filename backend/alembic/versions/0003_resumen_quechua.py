"""Fase 5: resumen en quechua por localidad (propuesto por una persona, validado por otra).

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op

from app.db import resumenes_quechua

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    resumenes_quechua.create(op.get_bind())


def downgrade() -> None:
    resumenes_quechua.drop(op.get_bind())
