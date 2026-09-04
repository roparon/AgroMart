from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.forms import RegisterForm, LoginForm
from app.models.user import User
from app.services.email_service import send_email

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("home.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        username_exists = User.query.filter_by(
            username=form.username.data).first()
        if username_exists:
            flash("Username already exists.", "danger")
            return render_template("register.html", form=form)
        email_exists = User.query.filter_by(
            email=form.email.data).first()
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
        send_email(
            subject="Welcome to Bomet Machineries Ltd",
            recipients=[user.email],
            template="emails/welcome.html",
            user=user,
        )


        flash(
            "Account created successfully. Please log in.",
            "success",
        )
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    # Already logged in
    if current_user.is_authenticated:

        if current_user.is_admin:
            return redirect(
                url_for("dashboard.dashboard")
            )

        return redirect(
            url_for("home.home")
        )

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            username=form.username.data.strip()
        ).first()

        # Validate credentials
        if user and user.check_password(
            form.password.data
        ):

            # Make sure the account is active
            if not user.is_active:

                flash(
                    "Your account has been deactivated. "
                    "Please contact support.",
                    "danger"
                )

                return render_template(
                    "login.html",
                    form=form
                )

            # Log the user in
            login_user(
                user,
                remember=form.remember.data
            )

            # Welcome message
            if user.is_admin:

                flash(
                    f"Welcome back, Admin {user.first_name}!",
                    "success"
                )

            else:

                flash(
                    f"Welcome back, {user.first_name}!",
                    "success"
                )

            # Respect Flask-Login's next parameter
            next_page = request.args.get("next")

            if next_page and next_page.startswith("/"):
                return redirect(next_page)

            # Admin → Admin Dashboard
            if user.is_admin:
                return redirect(
                    url_for("dashboard.dashboard")
                )

            # Customer → Storefront
            return redirect(
                url_for("home.home")
            )

        # Invalid credentials
        flash(
            "Invalid username or password.",
            "danger"
        )

    return render_template(
        "login.html",
        form=form
    )

# ============================================================
# ACCOUNT DASHBOARD
# ============================================================

@auth_bp.route("/account")
@login_required
def account():

    # All orders belonging to the logged-in customer
    orders = (
        current_user.orders
        if current_user.orders
        else []
    )

    # Order statistics
    total_orders = len(orders)

    pending_orders = sum(
        1
        for order in orders
        if order.status == "Pending"
    )

    processing_orders = sum(
        1
        for order in orders
        if order.status == "Processing"
    )

    shipped_orders = sum(
        1
        for order in orders
        if order.status == "Shipped"
    )

    delivered_orders = sum(
        1
        for order in orders
        if order.status == "Delivered"
    )

    # Total amount spent
    total_spent = sum(
        order.total_amount
        for order in orders
        if order.status != "Cancelled"
    )

    # Most recent orders
    recent_orders = sorted(
        orders,
        key=lambda order: order.created_at,
        reverse=True
    )[:5]

    return render_template(
        "account.html",
        total_orders=total_orders,
        pending_orders=pending_orders,
        processing_orders=processing_orders,
        shipped_orders=shipped_orders,
        delivered_orders=delivered_orders,
        total_spent=total_spent,
        recent_orders=recent_orders,
    )


@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "info",
    )

    return redirect(
        url_for("home.home")
    )