"""Add homepage sections and homepage settings

Revision ID: c8a4f91e2b73
Revises: 7f6f1d60b417
Create Date: 2026-09-20
"""

from alembic import op
import sqlalchemy as sa


revision = "c8a4f91e2b73"
down_revision = "7f6f1d60b417"
branch_labels = None
depends_on = None


def upgrade():

    # --------------------------------------------------------
    # HOMEPAGE SECTIONS
    # --------------------------------------------------------
    op.create_table(
        "homepage_sections",

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
            "section_type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "subtitle",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "content",
            sa.Text(),
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
            "config",
            sa.JSON(),
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
            nullable=True,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "key",
            name="uq_homepage_sections_key",
        ),
    )

    op.create_index(
        "ix_homepage_sections_key",
        "homepage_sections",
        ["key"],
        unique=True,
    )

    op.create_index(
        "ix_homepage_sections_section_type",
        "homepage_sections",
        ["section_type"],
        unique=False,
    )

    op.create_index(
        "ix_homepage_sections_is_active",
        "homepage_sections",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_homepage_sections_sort_order",
        "homepage_sections",
        ["sort_order"],
        unique=False,
    )


    # --------------------------------------------------------
    # HOMEPAGE SETTINGS
    # --------------------------------------------------------
    op.create_table(
        "homepage_settings",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "site_title",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "meta_description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "meta_keywords",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "og_image_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "announcement_text",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "announcement_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "announcement_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.func.now(),
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_homepage_settings_announcement_active",
        "homepage_settings",
        ["announcement_active"],
        unique=False,
    )

    op.create_index(
        "ix_homepage_settings_is_active",
        "homepage_settings",
        ["is_active"],
        unique=False,
    )


def downgrade():

    op.drop_index(
        "ix_homepage_settings_is_active",
        table_name="homepage_settings",
    )

    op.drop_index(
        "ix_homepage_settings_announcement_active",
        table_name="homepage_settings",
    )

    op.drop_table("homepage_settings")


    op.drop_index(
        "ix_homepage_sections_sort_order",
        table_name="homepage_sections",
    )

    op.drop_index(
        "ix_homepage_sections_is_active",
        table_name="homepage_sections",
    )

    op.drop_index(
        "ix_homepage_sections_section_type",
        table_name="homepage_sections",
    )

    op.drop_index(
        "ix_homepage_sections_key",
        table_name="homepage_sections",
    )

    op.drop_table("homepage_sections")
