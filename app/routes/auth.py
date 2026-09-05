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



# ============================================================
# LOGIN
# ============================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    if current_user.is_authenticated:

        # Admin → Admin Dashboard
        if current_user.is_admin:
            return redirect(
                url_for("dashboard.dashboard")
            )

        # Customer → Storefront
        return redirect(
            url_for("home.home")
        )


    # --------------------------------------------------------
    # Login form
    # --------------------------------------------------------

    form = LoginForm()


    if form.validate_on_submit():

        username = form.username.data.strip()

        user = User.query.filter_by(
            username=username
        ).first()


        # ----------------------------------------------------
        # Validate credentials
        # ----------------------------------------------------

        if user and user.check_password(
            form.password.data
        ):

            # ------------------------------------------------
            # Make sure account is active
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Log user in
            # ------------------------------------------------

            login_user(
                user,
                remember=form.remember.data
            )


            # ------------------------------------------------
            # Welcome message
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Respect Flask-Login "next" parameter
            # ------------------------------------------------

            next_page = request.args.get("next")


            if next_page and next_page.startswith("/"):

                return redirect(next_page)


            # ------------------------------------------------
            # Admin → Admin Dashboard
            # ------------------------------------------------

            if user.is_admin:

                return redirect(
                    url_for("dashboard.dashboard")
                )


            # ------------------------------------------------
            # Customer → Storefront
            # ------------------------------------------------

            return redirect(
                url_for("home.home")
            )


        # ----------------------------------------------------
        # Invalid credentials
        # ----------------------------------------------------

        flash(
            "Invalid username or password.",
            "danger"
        )


    return render_template(
        "login.html",
        form=form
    )


# ============================================================
# ADMIN PROFILE
# ============================================================

@auth_bp.route("/admin/profile")
@login_required
def admin_profile():

    # --------------------------------------------------------
    # Only administrators can access this page
    # --------------------------------------------------------

    if not current_user.is_admin:

        flash(
            "Access denied. Administrator privileges required.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )


    return render_template(
        "admin/profile.html"
    )

@auth_bp.route("/admin/profile/edit", methods=["GET", "POST"])
@login_required
def edit_admin_profile():

    # --------------------------------------------------------
    # Admin-only access
    # --------------------------------------------------------

    if not current_user.is_admin:

        flash(
            "Access denied. Administrator privileges required.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )


    # --------------------------------------------------------
    # Handle form submission
    # --------------------------------------------------------

    if request.method == "POST":

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        last_name = request.form.get(
            "last_name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()


        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        if not first_name or not last_name:

            flash(
                "First name and last name are required.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )


        if not username:

            flash(
                "Username is required.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )


        if not email:

            flash(
                "Email address is required.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )


        # ----------------------------------------------------
        # Check username uniqueness
        # ----------------------------------------------------

        existing_username = User.query.filter(
            User.username == username,
            User.id != current_user.id
        ).first()


        if existing_username:

            flash(
                "That username is already in use.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )


        # ----------------------------------------------------
        # Check email uniqueness
        # ----------------------------------------------------

        existing_email = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()


        if existing_email:

            flash(
                "That email address is already registered.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )


        # ----------------------------------------------------
        # Update profile
        # ----------------------------------------------------

        try:

            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.username = username
            current_user.email = email
            current_user.phone = phone or None
            current_user.address = address or None

            db.session.commit()


            flash(
                "Your administrator profile has been updated successfully.",
                "success"
            )

            return redirect(
                url_for("auth.admin_profile")
            )


        except Exception as e:

            db.session.rollback()

            print(
                f"ADMIN PROFILE UPDATE FAILED: {e}"
            )

            flash(
                "Unable to update your profile. Please try again.",
                "danger"
            )


    return render_template(
        "admin/edit_profile.html"
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


# ============================================================
# CHANGE PASSWORD
# ============================================================

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    # --------------------------------------------------------
    # Only administrators can use this page
    # --------------------------------------------------------

    if not current_user.is_admin:

        flash(
            "Access denied. Administrator privileges required.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )


    # --------------------------------------------------------
    # Handle password change
    # --------------------------------------------------------

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # ----------------------------------------------------
        # Validate current password
        # ----------------------------------------------------

        if not current_password:

            flash(
                "Please enter your current password.",
                "danger"
            )

            return render_template(
                "admin/change_password.html"
            )


        if not current_user.check_password(
            current_password
        ):

            flash(
                "Your current password is incorrect.",
                "danger"
            )

            return render_template(
                "admin/change_password.html"
            )


        # ----------------------------------------------------
        # Validate new password
        # ----------------------------------------------------

        if not new_password:

            flash(
                "Please enter a new password.",
                "danger"
            )

            return render_template(
                "admin/change_password.html"
            )


        # Minimum password length

        if len(new_password) < 8:

            flash(
                "Your new password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "admin/change_password.html"
            )


        # ----------------------------------------------------
        # Confirm password
        # ----------------------------------------------------

        if new_password != confirm_password:

            flash(
                "The new passwords do not match.",
                "danger"
            )

            return render_template(
                "admin/change_password.html"
            )


        # ----------------------------------------------------
        # Prevent using the same password
        # ----------------------------------------------------

        if current_user.check_password(
            new_password
        ):

            flash(
                "Your new password must be different from your current password.",
                "warning"
            )

            return render_template(
                "admin/change_password.html"
            )


        # ----------------------------------------------------
        # Update password
        # ----------------------------------------------------

        try:

            current_user.set_password(
                new_password
            )

            db.session.commit()


            flash(
                "Your password has been changed successfully.",
                "success"
            )

            return redirect(
                url_for("auth.admin_profile")
            )


        except Exception as e:

            db.session.rollback()

            print(
                f"PASSWORD CHANGE FAILED: {e}"
            )

            flash(
                "Unable to change your password. Please try again.",
                "danger"
            )


    # --------------------------------------------------------
    # Display password page
    # --------------------------------------------------------

    return render_template(
        "admin/change_password.html"
    )