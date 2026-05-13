import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use psycopg2 (sync driver) for migrations, not asyncpg
sqlalchemy_url = os.getenv("DATABASE_AUTH_URL", "postgresql+psycopg2://postgres@postgres:5432/voiceagent_auth")

if "asyncpg" in sqlalchemy_url:
    sqlalchemy_url = sqlalchemy_url.replace("+asyncpg", "+psycopg2")

config.set_main_option("sqlalchemy.url", sqlalchemy_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
