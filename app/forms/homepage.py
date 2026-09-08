from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField

from wtforms import (
    BooleanField,
    IntegerField,
    StringField,
    SubmitField,
    TextAreaField,
)

from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
)


class HomepageContentForm(FlaskForm):
    """
    Form for managing the existing HomepageContent records.

    This remains separate from HomepageSectionForm so the
    existing homepage content system continues to work.
    """

    key = StringField(
        "Content Key",
        validators=[
            DataRequired(
                message="A content key is required."
            ),
            Length(
                min=2,
                max=100,
                message="Content key must be between 2 and 100 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. hero_1, section_milling",
        },
    )

    headline = StringField(
        "Headline",
        validators=[
            Optional(),
            Length(
                max=255,
                message="Headline cannot exceed 255 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Enter headline",
        },
    )

    subheadline = TextAreaField(
        "Subheadline / Description",
        validators=[
            Optional(),
            Length(
                max=5000,
                message="Description cannot exceed 5,000 characters.",
            ),
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
            Length(
                max=100,
                message="Button text cannot exceed 100 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. Shop Now",
        },
    )

    button_url = StringField(
        "Button URL",
        validators=[
            Optional(),
            Length(
                max=500,
                message="Button URL cannot exceed 500 characters.",
            ),
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
        ],
    )

    image_alt = StringField(
        "Image Alt Text",
        validators=[
            Optional(),
            Length(
                max=255,
                message="Image alt text cannot exceed 255 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Describe the image for accessibility",
        },
    )

    css_class = StringField(
        "CSS Class",
        validators=[
            Optional(),
            Length(
                max=255,
                message="CSS class cannot exceed 255 characters.",
            ),
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
            NumberRange(
                min=0,
                max=9999,
                message="Display order must be between 0 and 9999.",
            ),
        ],
        default=0,
        render_kw={
            "min": 0,
            "max": 9999,
        },
    )

    submit = SubmitField(
        "Save Content"
    )