from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import MetaData, engine_from_config, inspect, pool, text
from sqlalchemy.engine import make_url

from app.canonical_schema import metadata as canonical_metadata
from app.executive_store import executive_metadata
from app.pod_store import pod_metadata
from app.resourcing_store import resourcing_metadata
from app.config import settings
from app.schema_integrity import attach_postgresql_integrity


config = context.config
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = MetaData()
for source in (canonical_metadata, pod_metadata, executive_metadata, resourcing_metadata):
    for table in source.sorted_tables:
        if table.name not in target_metadata.tables:
            table.to_metadata(target_metadata)

if make_url(config.get_main_option("sqlalchemy.url")).get_backend_name() == "postgresql":
    attach_postgresql_integrity(target_metadata)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    # Run the one-time SQLite compatibility rewrite in its own committed
    # transaction. Keeping it outside Alembic's connection avoids leaving an
    # implicit transaction open before the migration context starts.
    if connectable.dialect.name == "sqlite":
        with connectable.begin() as compatibility_connection:
            if inspect(compatibility_connection).has_table("alembic_version"):
                compatibility_connection.execute(text(
                    "UPDATE alembic_version SET version_num = '0004_reference_integrity' "
                    "WHERE version_num = '0004_complete_reference_integrity'"
                ))
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
