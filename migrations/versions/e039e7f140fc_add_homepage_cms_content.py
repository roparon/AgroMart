"""Add homepage CMS content

Revision ID: e039e7f140fc
Revises: 6e30027d9a8f
Create Date: 2026-09-05

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "e039e7f140fc"
down_revision = "6e30027d9a8f"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # --------------------------------------------------------
    # HOMEPAGE CMS CONTENT
    # --------------------------------------------------------

    op.create_table(
        "homepage_content",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "key",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "headline",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "subheadline",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "button_text",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "button_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "image_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "image_alt",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "css_class",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "key",
            name="uq_homepage_content_key",
        ),
    )


    # --------------------------------------------------------
    # INDEXES
    # --------------------------------------------------------

    op.create_index(
        "ix_homepage_content_key",
        "homepage_content",
        ["key"],
        unique=False,
    )

    op.create_index(
        "ix_homepage_content_is_active",
        "homepage_content",
        ["is_active"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # --------------------------------------------------------
    # DROP INDEXES FIRST
    # --------------------------------------------------------

    op.drop_index(
        "ix_homepage_content_is_active",
        table_name="homepage_content",
    )

    op.drop_index(
        "ix_homepage_content_key",
        table_name="homepage_content",
    )


    # --------------------------------------------------------
    # DROP TABLE
    # --------------------------------------------------------

    op.drop_table("homepage_content")
