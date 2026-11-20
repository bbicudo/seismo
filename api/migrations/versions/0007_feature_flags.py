"""feature flags: liga e desliga cada parte do site e cada coleta pela área administrativa

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE feature_flags (
          key        text PRIMARY KEY,
          enabled    boolean NOT NULL DEFAULT true,
          updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE feature_flags")
