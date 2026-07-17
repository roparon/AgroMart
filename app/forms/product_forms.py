from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField, BooleanField, SelectField, SubmitField)
from wtforms.validators import DataRequired, NumberRange





class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    price = DecimalField("Price (KSh)", validators=[DataRequired(), NumberRange(min=0)], places=2)
    stock = IntegerField("Stock Quantity", validators=[DataRequired(), NumberRange(min=0)])
    sku = StringField("SKU")
    category = SelectField("Category", coerce=int, validators=[DataRequired()])
    featured = BooleanField("Featured Product")
    submit = SubmitField("Save Product")