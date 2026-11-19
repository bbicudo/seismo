from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    seismo_env: str = "lab"
    postgres_host: str = "postgres"
    postgres_db: str = "seismo"
    postgres_user: str = "seismo"
    postgres_password_file: str = "/run/secrets/postgres_password"
    redis_url: str = "redis://redis:6379/0"

    def _password(self) -> str:
        return Path(self.postgres_password_file).read_text().strip()

    @property
    def postgres_dsn(self) -> str:
        return f"host={self.postgres_host} dbname={self.postgres_db} user={self.postgres_user} password={self._password()}"

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{quote(self._password(), safe='')}"
            f"@{self.postgres_host}/{self.postgres_db}"
        )
