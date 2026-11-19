from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from seismo_api.settings import Settings

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)


def run_migrations_online() -> None:
    engine = create_engine(Settings().sqlalchemy_url)
    with engine.connect() as conn:
        context.configure(connection=conn)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
