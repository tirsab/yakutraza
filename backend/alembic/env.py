from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings
from app.db import metadata

config = context.config
target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url") or get_settings().database_url,
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conexion = config.attributes.get("connection")
    if conexion is not None:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(config.get_main_option("sqlalchemy.url") or get_settings().database_url)
    with engine.connect() as cx:
        context.configure(connection=cx, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
