"""tipo de BattlEye do mundo: green (desde o lançamento) ou yellow (adicionado depois)

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE worlds ADD COLUMN battleye_type text")


def downgrade() -> None:
    op.execute("ALTER TABLE worlds DROP COLUMN battleye_type")
