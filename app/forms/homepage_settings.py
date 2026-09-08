from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import Optional, Length


class HomepageSettingsForm(FlaskForm):
    site_title = StringField(
        "Homepage / Site Title",
        validators=[
            Optional(),
            Length(max=255),
        ],
        render_kw={
            "placeholder": "Bomet Machineries Ltd. | Agricultural Machinery & Equipment",
        },
    )

    meta_description = TextAreaField(
        "Meta Description",
        validators=[
            Optional(),
            Length(max=500),
        ],
        render_kw={
            "rows": 4,
            "placeholder": (
                "Describe Bomet Machineries Ltd. for search engines..."
            ),
        },
    )

    meta_keywords = TextAreaField(
        "Meta Keywords",
        validators=[
            Optional(),
            Length(max=1000),
        ],
        render_kw={
            "rows": 3,
            "placeholder": (
                "posho mills, maize shellers, chaff cutters, generators, "
                "water pumps, agricultural machinery"
            ),
        },
    )

    og_image_url = StringField(
        "Social Sharing Image URL",
        validators=[
            Optional(),
            Length(max=500),
        ],
        render_kw={
            "placeholder": "/static/uploads/home/og-image.jpg",
        },
    )

    announcement_text = StringField(
        "Announcement Text",
        validators=[
            Optional(),
            Length(max=500),
        ],
        render_kw={
            "placeholder": "Special offer: Quality agricultural machinery available now",
        },
    )

    announcement_url = StringField(
        "Announcement Link",
        validators=[
            Optional(),
            Length(max=500),
        ],
        render_kw={
            "placeholder": "/products",
        },
    )

    announcement_active = BooleanField(
        "Show Announcement Bar",
        default=False,
    )

    is_active = BooleanField(
        "Enable Homepage",
        default=True,
    )

    submit = SubmitField(
        "Save Homepage Settings"
    )