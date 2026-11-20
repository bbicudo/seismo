from pathlib import Path

from pydantic_settings import BaseSettings

from . import __version__


class Settings(BaseSettings):
    seismo_env: str = "lab"
    seismo_paused: bool = True
    seismo_worlds: str = "all"
    seismo_contact: str = ""
    tibiadata_base: str = "https://api.tibiadata.com/v4"
    collect_interval_seconds: int = 300
    max_concurrency: int = 2
    max_rps: float = 2.0
    request_timeout: float = 20.0
    max_retries: int = 4
    # se a última foto boa de um mundo for mais velha que isso, não somamos minutos da sessão
    stale_after_seconds: int = 900

    # coletas diárias (rodam nas folgas da coleta de online)
    daily_jobs_enabled: bool = True
    guild_refresh_days: int = 3            # cada guild é lida de novo a cada N dias
    house_detail_daily_budget: int = 30000  # teto próprio da leitura de donos de casa por dia
    # teto de requisições à TibiaData por dia (UTC). A foto de online e as coletas diárias nunca são cortadas;
    # a leitura de donos de casa e de membros de guild se ajusta para o total não passar disso.
    daily_request_cap: int = 34000

    postgres_host: str = "postgres"
    postgres_db: str = "seismo"
    postgres_user: str = "seismo"
    postgres_password_file: str = "/run/secrets/postgres_password"
    redis_url: str = "redis://redis:6379/0"

    @property
    def user_agent(self) -> str:
        contact = f"; contact: {self.seismo_contact}" if self.seismo_contact else ""
        return f"Seismo/{__version__} (Tibia fansite collector, {self.seismo_env}{contact})"

    @property
    def postgres_dsn(self) -> str:
        password = Path(self.postgres_password_file).read_text().strip()
        return (
            f"host={self.postgres_host} dbname={self.postgres_db} "
            f"user={self.postgres_user} password={password}"
        )

    def target_worlds(self, available: list[str]) -> list[str]:
        if self.seismo_worlds.strip().lower() == "all":
            return sorted(available)
        wanted = {w.strip().lower() for w in self.seismo_worlds.split(",") if w.strip()}
        return sorted(w for w in available if w.lower() in wanted)
