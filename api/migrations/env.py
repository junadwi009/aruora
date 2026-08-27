import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.data.models import Base

config = context.config
if config.config_file_name:
    # disable_existing_loggers must stay False: when migrations run in-process
    # (tests, embedded tooling) the default True silently disables every
    # logger created before this point — including app.* telemetry — for the
    # rest of the process (WS10).
    fileConfig(config.config_file_name, disable_existing_loggers=False)
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
