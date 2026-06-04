"""phase7_schema

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5a6b7
Create Date: 2026-06-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("offers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("error_note", sa.Text(), nullable=True))

    with op.batch_alter_table("run_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tokens_consumidos", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("coste_estimado_eur", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_logs", schema=None) as batch_op:
        batch_op.drop_column("coste_estimado_eur")
        batch_op.drop_column("tokens_consumidos")

    with op.batch_alter_table("offers", schema=None) as batch_op:
        batch_op.drop_column("error_note")
