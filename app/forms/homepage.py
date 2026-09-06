from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize, FileRequired
from wtforms import (
    StringField,
    TextAreaField,
    BooleanField,
    IntegerField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional, URL, NumberRange


class HomepageContentForm(FlaskForm):
    key = StringField(
        "Content Key",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
        render_kw={
            "placeholder": "e.g. hero_1, section_milling",
        },
    )

    headline = StringField(
        "Headline",
        validators=[
            Optional(),
            Length(max=255),
        ],
        render_kw={
            "placeholder": "Enter headline",
        },
    )

    subheadline = TextAreaField(
        "Subheadline / Description",
        validators=[
            Optional(),
        ],
        render_kw={
            "rows": 5,
            "placeholder": "Enter supporting text...",
        },
    )

    button_text = StringField(
        "Button Text",
        validators=[
            Optional(),
            Length(max=100),
        ],
        render_kw={
            "placeholder": "e.g. Shop Now",
        },
    )

    button_url = StringField(
        "Button URL",
        validators=[
            Optional(),
            Length(max=500),
        ],
        render_kw={
            "placeholder": "/products",
        },
    )

    image = FileField(
        "Homepage Image",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
            ),
            FileSize(
                max_size=5 * 1024 * 1024,
                message="Image must be smaller than 5 MB.",
            ),
        ],
    )

    image_alt = StringField(
        "Image Alt Text",
        validators=[
            Optional(),
            Length(max=255),
        ],
        render_kw={
            "placeholder": "Describe the image for accessibility",
        },
    )

    css_class = StringField(
        "CSS Class",
        validators=[
            Optional(),
            Length(max=255),
        ],
        render_kw={
            "placeholder": "Optional CSS class",
        },
    )

    is_active = BooleanField(
        "Publish this content",
        default=True,
    )

    sort_order = IntegerField(
        "Display Order",
        validators=[
            Optional(),
            NumberRange(min=0),
        ],
        default=0,
    )

    submit = SubmitField("Save Content")