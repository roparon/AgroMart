from app import db


class HomepageSetting(db.Model):
    """
    Global settings for the Bomet Machineries Ltd. homepage.

    This model controls information that applies to the entire
    homepage rather than a single section.
    """

    __tablename__ = "homepage_settings"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    # Browser / SEO
    site_title = db.Column(
        db.String(255),
        nullable=True,
    )

    meta_description = db.Column(
        db.Text,
        nullable=True,
    )

    meta_keywords = db.Column(
        db.Text,
        nullable=True,
    )

    # Social sharing / Open Graph
    og_image_url = db.Column(
        db.String(500),
        nullable=True,
    )

    # Optional announcement bar
    announcement_text = db.Column(
        db.String(500),
        nullable=True,
    )

    announcement_url = db.Column(
        db.String(500),
        nullable=True,
    )

    announcement_active = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Homepage-wide publishing switch.
    is_active = db.Column(
        db.Boolean,
        default=True,
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
        return f"<HomepageSetting {self.site_title}>"