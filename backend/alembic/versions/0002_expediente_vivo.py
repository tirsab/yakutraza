"""Fase 3: documentos registrados, eventos de plazo y bitácora de solo agregado.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""
from alembic import op

from app.db import bitacora, documentos, eventos_plazo

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MENSAJE = "La bitácora es de solo agregado: no se puede modificar ni borrar"


def upgrade() -> None:
    bind = op.get_bind()
    for t in (documentos, eventos_plazo, bitacora):
        t.create(bind)
    if bind.dialect.name == "postgresql":
        op.execute(f"""
            CREATE FUNCTION bitacora_solo_agregar() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{MENSAJE}';
            END;
            $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE TRIGGER bitacora_sin_cambios BEFORE UPDATE OR DELETE ON bitacora
            FOR EACH ROW EXECUTE FUNCTION bitacora_solo_agregar();
        """)
    elif bind.dialect.name == "sqlite":
        for evento in ("UPDATE", "DELETE"):
            op.execute(f"""
                CREATE TRIGGER bitacora_sin_{evento.lower()} BEFORE {evento} ON bitacora
                BEGIN SELECT RAISE(ABORT, '{MENSAJE}'); END;
            """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS bitacora_sin_cambios ON bitacora")
        op.execute("DROP FUNCTION IF EXISTS bitacora_solo_agregar()")
    for t in (bitacora, eventos_plazo, documentos):
        t.drop(bind)
