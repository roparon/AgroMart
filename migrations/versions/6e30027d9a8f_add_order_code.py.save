"""add order code

Revision ID: 6e30027d9a8f
Revises: 503bc7625584
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers
revision = "6e30027d9a8f"
down_revision = "503bc7625584"
branch_labels = None
depends_on = None


def upgrade():

    # 1. Add the column temporarily as nullable
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "order_code",
                sa.String(length=30),
                nullable=True,
            )
        )

    # 2. Give every existing order a unique order code
    connection = op.get_bind()

    orders = connection.execute(
        sa.text("SELECT id FROM orders")
    ).fetchall()

    for order in orders:
        order_code = f"AGM-{uuid.uuid4().hex[:10].upper()}"

        connection.execute(
            sa.text(
                """
                UPDATE orders
                SET order_code = :order_code
                WHERE id = :order_id
                """
            ),
            {
                "order_code": order_code,
                "order_id": order.id,
            },
        )

    # 3. Make order_code required and unique
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column(
            "order_code",
            existing_type=sa.String(length=30),
            nullable=False,
        )

        batch_op.create_unique_constraint(
            "uq_orders_order_code",
            ["order_code"],
        )


def downgrade():

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_orders_order_code",
            type_="unique",
        )

        batch_op.drop_column("order_code")
