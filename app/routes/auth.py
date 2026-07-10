from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.forms import RegisterForm, LoginForm
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("home.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        username_exists = User.query.filter_by(
            username=form.username.data
        ).first()
        if username_exists:
            flash("Username already exists.", "danger")
            return render_template("register.html", form=form)
        email_exists = User.query.filter_by(
            email=form.email.data
        ).first()
        if email_exists:
            flash("Email already exists.", "danger")
            return render_template("register.html", form=form)
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data
        ).first()
        if user and user.check_password(form.password.data):

            login_user(
                user,
                remember=form.remember.data
            )

            flash("Welcome back!", "success")

            return redirect(url_for("home.home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "info")

    return redirect(url_for("home.home"))