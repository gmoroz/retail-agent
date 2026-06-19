"""Alembic migration environment.

The connection URL is injected from ``retail_agent.config`` (``DB_URI``), not read
from ``alembic.ini``, so credentials never land in version control.

Only Golden-bucket tables are migrated here. The LangGraph ``PostgresSaver``
creates its own checkpointer tables via ``.setup()`` at runtime, so they are
intentionally absent from ``target_metadata``.
"""

from sqlalchemy import engine_from_config, pool

from alembic import context
from retail_agent.config import get_settings
from retail_agent.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().sqlalchemy_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
