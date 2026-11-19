"""opt-out: pedidos com código de verificação no comentário do personagem

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL = """
CREATE TABLE optout_requests (
  id          bigserial PRIMARY KEY,
  name        text        NOT NULL,
  code        text        NOT NULL,
  status      text        NOT NULL DEFAULT 'pending',   -- pending | checking | verified | failed
  message     text,
  attempts    integer     NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL,
  checked_at  timestamptz
);
CREATE INDEX optout_requests_name ON optout_requests (lower(name), created_at DESC);
CREATE UNIQUE INDEX privacy_optouts_lower ON privacy_optouts (lower(name))
"""


def upgrade() -> None:
    for stmt in SQL.split(";"):
        if stmt.strip():
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP INDEX privacy_optouts_lower")
    op.execute("DROP TABLE optout_requests")
