from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, TelField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Regexp, Optional)


class RegisterForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2, max=100)])
    username = StringField("Username",validators=[DataRequired(), Length(min=3, max=50), Regexp(r'^[A-Za-z0-9_]+$', message="Username can only contain letters, numbers and underscores.")])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    phone = TelField("Phone Number", validators=[Optional(), Regexp(r'^(?:\+254|0)?[17]\d{8}$', message="Enter a valid Kenyan phone number.")])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64, message="Password must be between 8 and 64 characters.")])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Create Account")