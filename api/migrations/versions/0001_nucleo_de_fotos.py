"""núcleo de fotos: mundos, série de online, personagens, minutos por dia, agregados anônimos

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def run_sql(sql: str) -> None:
    # um comando por vez: o driver não aceita vários comandos num execute com parâmetros
    for stmt in sql.split(";"):
        if stmt.strip():
            op.execute(stmt)


def upgrade() -> None:
    run_sql(
        """
        CREATE TABLE worlds (
          id                 serial PRIMARY KEY,
          name               text NOT NULL UNIQUE,
          location           text,
          pvp_type           text,
          battleye_protected boolean,
          transfer_type      text,
          game_world_type    text,
          players_online     integer NOT NULL DEFAULT 0,
          first_seen         timestamptz NOT NULL DEFAULT now(),
          updated_at         timestamptz NOT NULL DEFAULT now()
        );

        -- uma linha por mundo a cada 5 min (vem de 1 requisição: /worlds)
        CREATE TABLE world_online_5m (
          world_id       integer NOT NULL REFERENCES worlds(id),
          ts             timestamptz NOT NULL,
          players_online integer NOT NULL,
          PRIMARY KEY (world_id, ts)
        );
        CREATE INDEX world_online_5m_ts ON world_online_5m (ts);

        -- privacidade: só o último DIA visto, nunca horários
        CREATE TABLE characters (
          id             bigserial PRIMARY KEY,
          name           text NOT NULL UNIQUE,
          world_id       integer REFERENCES worlds(id),
          level          integer NOT NULL,
          vocation       text NOT NULL,
          first_seen_day date NOT NULL,
          last_seen_day  date NOT NULL
        );
        CREATE INDEX characters_world ON characters (world_id);

        CREATE TABLE daily_online (
          character_id bigint  NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
          game_day     date    NOT NULL,
          minutes      integer NOT NULL DEFAULT 0,
          PRIMARY KEY (character_id, game_day)
        );
        CREATE INDEX daily_online_day ON daily_online (game_day);

        CREATE TABLE monthly_level (
          character_id bigint  NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
          month        date    NOT NULL,
          level_start  integer NOT NULL,
          level_end    integer NOT NULL,
          PRIMARY KEY (character_id, month)
        );

        CREATE TABLE transfers (
          id            bigserial PRIMARY KEY,
          character_id  bigint  NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
          from_world_id integer NOT NULL REFERENCES worlds(id),
          to_world_id   integer NOT NULL REFERENCES worlds(id),
          detected_day  date    NOT NULL,
          UNIQUE (character_id, detected_day, to_world_id)
        );

        -- agregado anônimo: soma de jogadores vistos por hora × vocação × faixa de level
        CREATE TABLE activity_buckets (
          world_id   integer NOT NULL REFERENCES worlds(id),
          hour       timestamptz NOT NULL,
          vocation   text NOT NULL,
          level_band text NOT NULL,
          samples    integer NOT NULL,
          PRIMARY KEY (world_id, hour, vocation, level_band)
        );

        -- quantas fotos entraram em cada hora (média = samples / snapshots)
        CREATE TABLE world_hour_snapshots (
          world_id  integer NOT NULL REFERENCES worlds(id),
          hour      timestamptz NOT NULL,
          snapshots integer NOT NULL,
          PRIMARY KEY (world_id, hour)
        );

        -- opt-out (usado a partir da fase do site público)
        CREATE TABLE privacy_optouts (
          name       text PRIMARY KEY,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE privacy_optouts, world_hour_snapshots, activity_buckets, transfers,
                   monthly_level, daily_online, characters, world_online_5m, worlds;
        """
    )
