"""add_research_ttl_to_companies

Revision ID: c2d3e4f5a6b7
Revises: bf4995253e8d
Create Date: 2026-05-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "bf4995253e8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("fecha_research", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("expira_en", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.drop_column("expira_en")
        batch_op.drop_column("fecha_research")
