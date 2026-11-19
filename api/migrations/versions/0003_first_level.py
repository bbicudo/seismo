"""level em que o personagem foi visto pela primeira vez (base da estimativa de personagens novos)

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE characters ADD COLUMN first_level integer")
    op.execute("CREATE INDEX characters_new ON characters (world_id, first_seen_day) WHERE first_level <= 7")


def downgrade() -> None:
    op.execute("DROP INDEX characters_new")
    op.execute("ALTER TABLE characters DROP COLUMN first_level")
