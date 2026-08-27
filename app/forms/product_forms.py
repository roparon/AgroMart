from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField, BooleanField, SelectField, SubmitField)
from wtforms.validators import (DataRequired, Optional, Length, NumberRange)
from flask_wtf.file import FileField, FileAllowed

class ProductForm(FlaskForm):

    name = StringField(
        "Product Name",
        validators=[
            DataRequired(),
            Length(min=2, max=200),
        ],
    )

    brand = StringField(
        "Brand",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    description = TextAreaField(
        "Description",
        validators=[
            DataRequired(),
        ],
    )

    price = DecimalField(
        "Price (KSh)",
        validators=[
            DataRequired(),
            NumberRange(min=0),
        ],
        places=2,
    )

    discount = IntegerField(
        "Discount (%)",
        validators=[
            Optional(),
            NumberRange(min=0, max=100),
        ],
        default=0,
    )

    stock = IntegerField(
        "Stock Quantity",
        validators=[
            DataRequired(),
            NumberRange(min=0),
        ],
    )

    sku = StringField(
        "SKU",
        validators=[
            Optional(),
            Length(max=100),
        ],
    )

    slug = StringField(
        "Slug",
        validators=[
            Optional(),
            Length(max=255),
        ],
    )

    category = SelectField(
        "Category",
        coerce=int,
        validators=[
            DataRequired(),
        ],
    )

    featured = BooleanField(
        "Featured Product",
    )

    is_active = BooleanField(
        "Active Product",
        default=True,
    )


    images = FileField(
    "Product Images",
    validators=[
        FileAllowed(
            ["jpg", "jpeg", "png", "webp"],
            "Images only: JPG, JPEG, PNG, or WEBP."
        )
    ],
    render_kw={
        "multiple": True
    },
)

    
    submit = SubmitField(
            "Save Product"
        )