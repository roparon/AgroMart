from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    BooleanField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
)


class CategoryForm(FlaskForm):

    name = StringField(
        "Category Name",
        validators=[
            DataRequired(
                message="Category name is required."
            ),
            Length(
                min=2,
                max=100,
                message="Category name must be between 2 and 100 characters."
            ),
        ],
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(
                max=1000,
                message="Description cannot exceed 1000 characters."
            ),
        ],
    )

    slug = StringField(
        "Slug",
        validators=[
            DataRequired(
                message="Slug is required."
            ),
            Length(
                min=2,
                max=150,
                message="Slug must be between 2 and 150 characters."
            ),
        ],
    )

    image_url = StringField(
        "Image URL",
        validators=[
            Optional(),
            Length(
                max=255,
                message="Image URL cannot exceed 255 characters."
            ),
        ],
    )

    is_active = BooleanField(
        "Active",
        default=True,
    )

    submit = SubmitField(
        "Save Category"
    )