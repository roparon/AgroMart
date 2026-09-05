from datetime import datetime

from app import db


class HomepageContent(db.Model):
    __tablename__ = "homepage_content"

    id = db.Column(db.Integer, primary_key=True)

    # Unique identifier used by the template.
    # Examples:
    # hero, hero_secondary, machinery_banner,
    # categories_heading, featured_heading
    key = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Text content
    headline = db.Column(db.String(255))
    subheadline = db.Column(db.Text)
    button_text = db.Column(db.String(100))
    button_url = db.Column(db.String(500))

    # Image
    image_url = db.Column(db.String(500))

    # Accessibility / SEO
    image_alt = db.Column(db.String(255))

    # Optional styling / positioning
    css_class = db.Column(db.String(255))

    # Publishing controls
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    sort_order = db.Column(
        db.Integer,
        default=0,
        nullable=False,
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
        return f"<HomepageContent {self.key}>"