"""raids: lista curada da TibiaWiki e ocorrências detectadas pelas kill statistics

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL = """
CREATE TABLE raids (
  id         serial PRIMARY KEY,
  slug       text   NOT NULL UNIQUE,
  name       text   NOT NULL,
  region     text   NOT NULL,
  creatures  text[] NOT NULL,
  race_keys  text[] NOT NULL,             -- nomes como aparecem nas kill statistics (minúsculas)
  signature  text[] NOT NULL DEFAULT '{}' -- criaturas raras que denunciam a raid (recalculado todo dia)
);

CREATE TABLE raid_occurrences (
  world_id integer NOT NULL REFERENCES worlds(id),
  raid_id  integer NOT NULL REFERENCES raids(id) ON DELETE CASCADE,
  day      date    NOT NULL,
  kills    integer NOT NULL,
  PRIMARY KEY (world_id, raid_id, day)
);
CREATE INDEX raid_occurrences_world_day ON raid_occurrences (world_id, day DESC)
"""


def upgrade() -> None:
    for stmt in SQL.split(";"):
        if stmt.strip():
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE raid_occurrences, raids")
