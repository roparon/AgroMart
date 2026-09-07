from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class CategoryForm(FlaskForm):
    name = StringField(
        "Category Name",
        validators=[
            DataRequired(message="Category name is required."),
            Length(
                min=2,
                max=100,
                message="Category name must be between 2 and 100 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. Posho Mills",
        },
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(
                max=1000,
                message="Description cannot exceed 1000 characters.",
            ),
        ],
        render_kw={
            "placeholder": "Enter a short description of this category...",
            "rows": 5,
        },
    )

    slug = StringField(
        "Slug",
        validators=[
            DataRequired(message="Slug is required."),
            Length(
                min=2,
                max=150,
                message="Slug must be between 2 and 150 characters.",
            ),
        ],
        render_kw={
            "placeholder": "e.g. posho-mills",
        },
    )

    image = FileField(
        "Category Image",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
            ),
        ],
    )

    is_active = BooleanField(
        "Active",
        default=True,
    )

    submit = SubmitField(
        "Save Category",
    )
