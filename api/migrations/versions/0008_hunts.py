"""hunts: áreas de caça da TibiaWiki, com posição no mapa e criaturas

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE hunts (
          slug      text PRIMARY KEY,
          name      text    NOT NULL,
          city      text,
          x         integer NOT NULL,
          y         integer NOT NULL,
          z         integer NOT NULL,
          creatures text[]  NOT NULL,
          race_keys text[]  NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE hunts")
