"""coletas diárias: kill statistics (raids), casas e leilões, guilds e membros

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = """
-- kill statistics do dia anterior (só linhas com algum valor diferente de zero)
CREATE TABLE kill_stats_daily (
  world_id       integer NOT NULL REFERENCES worlds(id),
  stats_day      date    NOT NULL,
  race           text    NOT NULL,
  killed         integer NOT NULL,
  players_killed integer NOT NULL,
  PRIMARY KEY (world_id, stats_day, race)
);
CREATE INDEX kill_stats_daily_race ON kill_stats_daily (race, stats_day);

-- casas e guildhalls (dados fixos)
CREATE TABLE houses (
  world_id           integer NOT NULL REFERENCES worlds(id),
  house_id           integer NOT NULL,
  town               text    NOT NULL,
  name               text    NOT NULL,
  kind               text    NOT NULL,           -- house | guildhall
  size               integer,
  rent               integer,
  beds               integer,
  needs_details      boolean NOT NULL DEFAULT true,
  details_fetched_at timestamptz,
  PRIMARY KEY (world_id, house_id)
);
CREATE INDEX houses_needs_details ON houses (needs_details) WHERE needs_details;

-- situação diária de cada casa
CREATE TABLE house_snapshots (
  world_id         integer NOT NULL,
  house_id         integer NOT NULL,
  snap_day         date    NOT NULL,
  rented           boolean NOT NULL,
  auctioned        boolean NOT NULL,
  current_bid      integer,
  time_left        text,
  auction_finished boolean,
  PRIMARY KEY (world_id, house_id, snap_day),
  FOREIGN KEY (world_id, house_id) REFERENCES houses(world_id, house_id)
);

-- histórico de donos (informação pública do tibia.com)
CREATE TABLE house_owners (
  id             bigserial PRIMARY KEY,
  world_id       integer NOT NULL,
  house_id       integer NOT NULL,
  owner          text    NOT NULL,
  first_seen_day date    NOT NULL,
  last_seen_day  date    NOT NULL,
  ended_day      date,
  FOREIGN KEY (world_id, house_id) REFERENCES houses(world_id, house_id)
);
CREATE INDEX house_owners_current ON house_owners (world_id, house_id) WHERE ended_day IS NULL;

CREATE TABLE guilds (
  id                 serial PRIMARY KEY,
  name               text    NOT NULL UNIQUE,
  world_id           integer NOT NULL REFERENCES worlds(id),
  in_formation       boolean NOT NULL DEFAULT false,
  logo_url           text,
  founded            date,
  members_total      integer,
  in_war             boolean,
  open_applications  boolean,
  guildhalls         integer,
  first_seen_day     date    NOT NULL,
  last_seen_day      date    NOT NULL,
  disbanded_day      date,
  details_fetched_at timestamptz
);
CREATE INDEX guilds_world ON guilds (world_id);
CREATE INDEX guilds_due ON guilds (details_fetched_at NULLS FIRST) WHERE disbanded_day IS NULL;

-- membros atuais (sem status online/offline: presença não é guardada)
CREATE TABLE guild_members (
  guild_id integer NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
  name     text    NOT NULL,
  rank     text,
  title    text,
  vocation text,
  level    integer,
  joined   date,
  PRIMARY KEY (guild_id, name)
);
CREATE INDEX guild_members_name ON guild_members (name);

-- entradas e saídas detectadas entre duas leituras da guild
CREATE TABLE guild_events (
  id        bigserial PRIMARY KEY,
  guild_id  integer NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
  name      text    NOT NULL,
  event     text    NOT NULL,                   -- join | leave
  event_day date    NOT NULL
);
CREATE INDEX guild_events_guild_day ON guild_events (guild_id, event_day)
"""


def upgrade() -> None:
    for stmt in SQL.split(";"):
        if stmt.strip():
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE guild_events, guild_members, guilds, house_owners, house_snapshots, houses, kill_stats_daily")
