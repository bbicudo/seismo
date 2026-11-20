"""eventos do jogo (double XP, rapid respawn, lua cheia...) e criatura/chefe em destaque do dia

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL = """
CREATE TABLE game_events (
  day    date NOT NULL,                 -- dia de jogo (vira no server save)
  name   text NOT NULL,
  kind   text NOT NULL,                 -- double_xp | double_skill | rapid_respawn | calendar
  source text NOT NULL,                 -- tibia.com (notícia) | tibiamarket (calendário comunitário)
  url    text,
  PRIMARY KEY (day, name)
);
CREATE INDEX game_events_kind ON game_events (kind, day);

CREATE TABLE daily_boosted (
  day      date PRIMARY KEY,
  creature text,
  boss     text
)
"""


def upgrade() -> None:
    for stmt in SQL.split(";"):
        if stmt.strip():
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE daily_boosted, game_events")
