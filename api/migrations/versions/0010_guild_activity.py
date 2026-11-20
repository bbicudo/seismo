"""mapa de calor por guild: soma de membros online por guild e hora (anônimo)

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE guild_activity_buckets (
          guild_id integer     NOT NULL REFERENCES guilds(id) ON DELETE CASCADE,
          hour     timestamptz NOT NULL,
          samples  integer     NOT NULL,
          PRIMARY KEY (guild_id, hour)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE guild_activity_buckets")
