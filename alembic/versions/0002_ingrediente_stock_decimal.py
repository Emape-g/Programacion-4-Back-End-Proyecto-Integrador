"""ingrediente stock decimal

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ingrediente",
        "stock_cantidad",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 3),
        existing_nullable=False,
        postgresql_using="stock_cantidad::numeric(10, 3)",
    )


def downgrade() -> None:
    op.alter_column(
        "ingrediente",
        "stock_cantidad",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="stock_cantidad::integer",
    )
