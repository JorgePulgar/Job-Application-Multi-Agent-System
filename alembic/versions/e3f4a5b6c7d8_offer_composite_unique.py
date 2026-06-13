"""offer per-user composite unique (user_id, hash_unico)

Replaces the global UNIQUE(hash_unico) with a composite UNIQUE(user_id,
hash_unico) so the same public job can be stored once per user instead of once
across all users. Without this, a second user's identical offer hit an
IntegrityError on the global constraint and was silently dropped.

Revision ID: e3f4a5b6c7d8
Revises: d1e2f3a4b5c6
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | Sequence[str] | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop global unique on hash_unico; add composite (user_id, hash_unico)."""
    with op.batch_alter_table("offers", schema=None) as batch_op:
        batch_op.drop_constraint("uq_offers_hash_unico", type_="unique")
        batch_op.create_unique_constraint("uq_offers_user_hash", ["user_id", "hash_unico"])


def downgrade() -> None:
    """Restore the global unique on hash_unico."""
    with op.batch_alter_table("offers", schema=None) as batch_op:
        batch_op.drop_constraint("uq_offers_user_hash", type_="unique")
        batch_op.create_unique_constraint("uq_offers_hash_unico", ["hash_unico"])
