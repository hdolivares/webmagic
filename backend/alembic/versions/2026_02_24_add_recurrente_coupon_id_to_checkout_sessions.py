"""Add recurrente_coupon_id to checkout_sessions

Revision ID: add_recurrente_coupon_id
Revises: add_checkout_sessions
Create Date: 2026-02-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "add_recurrente_coupon_id"
down_revision: Union[str, None] = "add_checkout_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkout_sessions",
        sa.Column(
            "recurrente_coupon_id",
            sa.String(255),
            nullable=True,
            comment="Recurrente coupon ID when created for abandoned cart recovery",
        ),
    )
    op.create_index(
        "idx_checkout_sessions_recurrente_coupon_id",
        "checkout_sessions",
        ["recurrente_coupon_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_checkout_sessions_recurrente_coupon_id", table_name="checkout_sessions")
    op.drop_column("checkout_sessions", "recurrente_coupon_id")
