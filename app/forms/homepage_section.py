from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    URL,
)


class HomepageSectionForm(FlaskForm):
    """
    Form used by administrators to create and edit
    homepage sections.
    """

    key = StringField(
        "Section Key",
        validators=[
            DataRequired(
                message="A section key is required."
            ),
            Length(
                min=2,
                max=100,
                message="Section key must be between 2 and 100 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. featured_categories",
        },
    )

    section_type = SelectField(
        "Section Type",
        choices=[
            ("hero", "Hero"),
            ("intro", "Introduction"),
            ("featured_categories", "Featured Categories"),
            ("product_grid", "Product Grid"),
            ("product_category", "Product Category"),
            ("image_text", "Image + Text"),
            ("trust", "Trust / Benefits"),
            ("services", "Services"),
            ("banner", "Banner"),
            ("cta", "Call to Action"),
            ("spare_parts", "Spare Parts"),
            ("custom_html", "Custom HTML"),
        ],
        validators=[
            DataRequired(
                message="Please select a section type."
            )
        ],
    )

    title = StringField(
        "Section Title",
        validators=[
            Optional(),
            Length(
                max=255,
                message="Title cannot exceed 255 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Enter the section title",
        },
    )

    subtitle = TextAreaField(
        "Subtitle",
        validators=[
            Optional(),
            Length(
                max=2000,
                message="Subtitle cannot exceed 2,000 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Enter supporting text...",
            "rows": 4,
        },
    )

    content = TextAreaField(
        "Section Content",
        validators=[
            Optional(),
        ],
        render_kw={
            "placeholder": "Enter the main section content...",
            "rows": 8,
        },
    )

    image = FileField(
        "Section Image",
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
                message="Alt text cannot exceed 255 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Describe the image for accessibility",
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
                message="URL cannot exceed 500 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. /products",
        },
    )

    config = TextAreaField(
        "Section Configuration",
        validators=[
            Optional(),
        ],
        render_kw={
            "placeholder": (
                '{\n'
                '  "limit": 6,\n'
                '  "layout": "grid"\n'
                '}'
            ),
            "rows": 8,
        },
    )

    css_class = StringField(
        "CSS Classes",
        validators=[
            Optional(),
            Length(
                max=255,
                message="CSS classes cannot exceed 255 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Optional CSS classes",
        },
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
            "placeholder": "0",
            "min": 0,
            "max": 9999,
        },
    )

    is_active = BooleanField(
        "Published",
        default=True,
    )

    submit = SubmitField(
        "Save Section"
    )