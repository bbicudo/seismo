"""sugestões de correção enviadas pelo site (sem IP nem dado pessoal)

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE feedback (
          id         serial      PRIMARY KEY,
          created_at timestamptz NOT NULL DEFAULT now(),
          feature    text        NOT NULL,
          page       text,
          message    text        NOT NULL,
          locale     text,
          resolved   boolean     NOT NULL DEFAULT false
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE feedback")
