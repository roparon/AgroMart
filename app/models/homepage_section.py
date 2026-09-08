from app import db


class HomepageSection(db.Model):
    """
    Database-driven homepage section.

    Each record represents one section/block that can be
    displayed on the Bomet Machineries Ltd. homepage.
    """

    __tablename__ = "homepage_sections"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # Unique internal identifier.
    # Examples:
    # hero
    # featured_categories
    # featured_products
    # machinery_showcase
    # trust
    # services
    # cta
    key = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Determines how index.html renders this section.
    #
    # Supported examples:
    # hero
    # intro
    # featured_categories
    # product_grid
    # product_category
    # image_text
    # trust
    # services
    # banner
    # cta
    # spare_parts
    # custom_html
    section_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    # Main section heading.
    title = db.Column(
        db.String(255),
        nullable=True,
    )

    # Supporting text.
    subtitle = db.Column(
        db.Text,
        nullable=True,
    )

    # Longer section content.
    content = db.Column(
        db.Text,
        nullable=True,
    )

    # Optional section image.
    image_url = db.Column(
        db.String(500),
        nullable=True,
    )

    # Accessibility / SEO.
    image_alt = db.Column(
        db.String(255),
        nullable=True,
    )

    # Optional CTA.
    button_text = db.Column(
        db.String(100),
        nullable=True,
    )

    button_url = db.Column(
        db.String(500),
        nullable=True,
    )

    # Flexible configuration for different section types.
    #
    # Examples:
    #
    # {
    #     "category_id": 5,
    #     "limit": 6,
    #     "layout": "grid"
    # }
    #
    # or:
    #
    # {
    #     "product_ids": [1, 4, 8],
    #     "layout": "featured"
    # }
    config = db.Column(
        db.JSON,
        nullable=True,
    )

    # Optional CSS classes controlled by the administrator.
    css_class = db.Column(
        db.String(255),
        nullable=True,
    )

    # Publishing status.
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Controls section position on the homepage.
    sort_order = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        index=True,
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    def __repr__(self):
        return (
            f"<HomepageSection "
            f"{self.key} "
            f"type={self.section_type}>"
        )