from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from database.db import Base
from config.settings import settings
import psycopg2
import re

# Import models for metadata discovery
try:
    import backend.db.models.schema
    import backend.db.models.transport_agent_models
except Exception:
    pass

db_url = settings.DATABASE_URL
is_pg = False

if "postgres" in db_url.lower():
    try:
        m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)", db_url)
        if m:
            user, password, host, port, dbname = m.groups()
            port = int(port) if port else 5432
            conn = psycopg2.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=dbname,
                connect_timeout=2
            )
            conn.close()
            is_pg = True
    except Exception:
        pass

if is_pg:
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
else:
    db_url = "sqlite:///agrinegotiator.db"
    print("WARNING: PostgreSQL not reachable for migrations. Falling back to sync SQLite: agrinegotiator.db")

config.set_main_option("sqlalchemy.url", db_url)
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = db_url.replace('+aiosqlite', '').replace('+asyncpg', '')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url.replace('+aiosqlite', '').replace('+asyncpg', '')
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
