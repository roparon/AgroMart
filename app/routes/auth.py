from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from hashlib import sha256
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app import db
from app.forms import RegisterForm, LoginForm
from app.models.user import User
from app.services.email_service import send_email


auth_bp = Blueprint("auth", __name__)


# ============================================================
# PASSWORD RESET HELPERS
# ============================================================

PASSWORD_RESET_MAX_AGE = 3600  # 1 hour


def _password_reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="agromart-password-reset",
    )


def _password_version(user):
    return sha256(
        user.password_hash.encode("utf-8")
    ).hexdigest()


def _generate_password_reset_token(user):
    return _password_reset_serializer().dumps(
        {
            "user_id": user.id,
            "password_version": _password_version(user),
        }
    )


def _load_password_reset_user(token):
    try:
        data = _password_reset_serializer().loads(
            token,
            max_age=PASSWORD_RESET_MAX_AGE,
        )

    except SignatureExpired:
        return None

    except BadSignature:
        return None

    user_id = data.get("user_id")
    password_version = data.get("password_version")

    if not user_id or not password_version:
        return None

    try:
        user = db.session.get(User, int(user_id))

    except (ValueError, TypeError):
        return None

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while validating a password reset token."
        )

        return None

    if not user:
        return None

    if not user.is_active:
        return None

    # A changed password creates a new hash, which invalidates
    # previously issued reset tokens automatically.
    if password_version != _password_version(user):
        return None

    return user


# ============================================================
# FORGOT PASSWORD
# ============================================================

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if current_user.is_authenticated:
        return redirect(url_for("home.home"))

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            flash(
                "Please enter your email address.",
                "danger"
            )

            return render_template(
                "forgot_password.html"
            )

        try:

            user = User.query.filter_by(
                email=email
            ).first()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while processing a password reset request."
            )

            # Do not reveal whether an account exists.
            flash(
                "If an account exists for that email address, "
                "password reset instructions have been sent.",
                "info"
            )

            return redirect(
                url_for("auth.login")
            )

        if user and user.is_active:

            try:

                token = _generate_password_reset_token(user)

                reset_url = url_for(
                    "auth.reset_password",
                    token=token,
                    _external=True,
                )

                email_sent = send_email(
                    subject="Reset Your Bomet Machineries Password",
                    recipients=[user.email],
                    template="emails/password_reset.html",
                    user=user,
                    reset_url=reset_url,
                    expires_minutes=PASSWORD_RESET_MAX_AGE // 60,
                )

                if not email_sent:

                    current_app.logger.warning(
                        "Password reset email could not be sent to %s.",
                        user.email,
                    )

            except Exception:

                current_app.logger.exception(
                    "Unexpected error while preparing password reset "
                    "email for user %s.",
                    user.id,
                )

        flash(
            "If an account exists for that email address, "
            "password reset instructions have been sent.",
            "info"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "forgot_password.html"
    )


# ============================================================
# REGISTER
# ============================================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("home.home"))

    form = RegisterForm()

    if form.validate_on_submit():

        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        # ----------------------------------------------------
        # Check username
        # ----------------------------------------------------

        try:

            username_exists = User.query.filter_by(
                username=username
            ).first()

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Database error while checking username during registration."
            )

            flash(
                "We could not process your registration right now. "
                "Please try again in a moment.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        if username_exists:

            flash(
                "Username already exists.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        # ----------------------------------------------------
        # Check email
        # ----------------------------------------------------

        try:

            email_exists = User.query.filter_by(
                email=email
            ).first()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while checking email during registration."
            )

            flash(
                "We could not process your registration right now. "
                "Please try again in a moment.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        if email_exists:

            flash(
                "Email already exists.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        # ----------------------------------------------------
        # Create user
        # ----------------------------------------------------

        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            username=username,
            email=email,
            phone=(form.phone.data.strip() if form.phone.data else None)
        )

        try:

            user.set_password(
                form.password.data
            )

            db.session.add(user)
            db.session.commit()

        except IntegrityError:

            db.session.rollback()

            current_app.logger.exception(
                "Registration failed because of a database integrity error."
            )

            flash(
                "We could not create your account because some of "
                "the information is already in use. Please check "
                "your username and email and try again.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while creating a new user."
            )

            flash(
                "We could not create your account right now. "
                "Please try again in a moment.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                "Unexpected error while creating a new user."
            )

            flash(
                "We could not create your account right now. "
                "Please try again in a moment.",
                "danger"
            )

            return render_template(
                "register.html",
                form=form
            )

        # ----------------------------------------------------
        # Welcome email
        #
        # Email is intentionally NOT part of the account
        # creation transaction.
        #
        # The account already exists successfully. If email
        # delivery fails, registration must still succeed.
        # ----------------------------------------------------

        try:

            email_sent = send_email(
                subject="Welcome to Bomet Machineries Ltd",
                recipients=[user.email],
                template="emails/welcome.html",
                user=user,
            )

            if not email_sent:

                current_app.logger.warning(
                    "Welcome email could not be sent to %s.",
                    user.email
                )

        except Exception:

            current_app.logger.exception(
                "Unexpected error while sending welcome email to %s.",
                user.email
            )

        # ----------------------------------------------------
        # Registration completed
        # ----------------------------------------------------

        flash(
            "Account created successfully. Please log in.",
            "success",
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "register.html",
        form=form
    )


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    # --------------------------------------------------------
    # Already logged in
    # --------------------------------------------------------

    if current_user.is_authenticated:

        if current_user.is_admin:

            return redirect(
                url_for("dashboard.dashboard")
            )

        return redirect(
            url_for("home.home")
        )

    # --------------------------------------------------------
    # Login form
    # --------------------------------------------------------

    form = LoginForm()

    if form.validate_on_submit():

        username = form.username.data.strip()

        try:

            user = User.query.filter_by(
                username=username
            ).first()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error during login."
            )

            flash(
                "We could not log you in right now. "
                "Please try again in a moment.",
                "danger"
            )

            return render_template(
                "login.html",
                form=form
            )

        # ----------------------------------------------------
        # Validate credentials
        # ----------------------------------------------------

        password_valid = False

        if user:

            try:

                password_valid = user.check_password(
                    form.password.data
                )

            except Exception:

                current_app.logger.exception(
                    "Password verification failed for username '%s'.",
                    username
                )

                password_valid = False

        if user and password_valid:

            # ------------------------------------------------
            # Check account status
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

            try:

                login_user(
                    user,
                    remember=form.remember.data
                )

            except Exception:

                current_app.logger.exception(
                    "Failed to create login session for user %s.",
                    user.id
                )

                flash(
                    "We could not log you in right now. "
                    "Please try again.",
                    "danger"
                )

                return render_template(
                    "login.html",
                    form=form
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
            # Respect Flask-Login next parameter
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
# RESET PASSWORD
# ============================================================

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    if current_user.is_authenticated:
        return redirect(url_for("home.home"))

    user = _load_password_reset_user(token)

    if not user:

        flash(
            "This password reset link is invalid or has expired. "
            "Please request a new one.",
            "danger"
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    if request.method == "POST":

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not new_password:

            flash(
                "Please enter a new password.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        if len(new_password) < 8:

            flash(
                "Your new password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        if new_password != confirm_password:

            flash(
                "The new passwords do not match.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        try:

            if user.check_password(new_password):

                flash(
                    "Your new password must be different from "
                    "your current password.",
                    "warning"
                )

                return render_template(
                    "reset_password.html"
                )

            user.set_password(new_password)

            db.session.commit()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while resetting password for user %s.",
                user.id,
            )

            flash(
                "Unable to reset your password right now. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                "Unexpected error while resetting password for user %s.",
                user.id,
            )

            flash(
                "Unable to reset your password right now. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        flash(
            "Your password has been reset successfully. "
            "You can now log in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "reset_password.html"
    )


# ============================================================
# ADMIN PROFILE
# ============================================================

@auth_bp.route("/admin/profile")
@login_required
def admin_profile():

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


# ============================================================
# EDIT ADMIN PROFILE
# ============================================================

@auth_bp.route("/admin/profile/edit", methods=["GET", "POST"])
@login_required
def edit_admin_profile():

    if not current_user.is_admin:

        flash(
            "Access denied. Administrator privileges required.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )

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

        try:

            existing_username = User.query.filter(
                User.username == username,
                User.id != current_user.id
            ).first()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while checking admin username."
            )

            flash(
                "We could not update your profile right now. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )

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

        try:

            existing_email = User.query.filter(
                User.email == email,
                User.id != current_user.id
            ).first()

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while checking admin email."
            )

            flash(
                "We could not update your profile right now. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/edit_profile.html"
            )

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

        except IntegrityError:

            db.session.rollback()

            current_app.logger.exception(
                "Admin profile update failed because of a database integrity error."
            )

            flash(
                "That username or email address is already in use.",
                "danger"
            )

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while updating admin profile."
            )

            flash(
                "Unable to update your profile right now. "
                "Please try again.",
                "danger"
            )

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                "Unexpected error while updating admin profile."
            )

            flash(
                "Unable to update your profile. "
                "Please try again.",
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

    try:

        orders = (
            current_user.orders
            if current_user.orders
            else []
        )

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

        total_spent = sum(
            order.total_amount
            for order in orders
            if order.status != "Cancelled"
        )

        recent_orders = sorted(
            orders,
            key=lambda order: order.created_at,
            reverse=True
        )[:5]

    except SQLAlchemyError:

        db.session.rollback()

        current_app.logger.exception(
            "Database error while loading account dashboard."
        )

        flash(
            "We could not load your account information right now. "
            "Please try again.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )

    except Exception:

        current_app.logger.exception(
            "Unexpected error while loading account dashboard."
        )

        flash(
            "We could not load your account information right now. "
            "Please try again.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )

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


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route("/logout")
@login_required
def logout():

    try:

        logout_user()

    except Exception:

        current_app.logger.exception(
            "Logout operation encountered an error."
        )

        flash(
            "There was a problem logging you out. "
            "Please try again.",
            "warning"
        )

        return redirect(
            url_for("home.home")
        )

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

    if not current_user.is_admin:

        flash(
            "Access denied. Administrator privileges required.",
            "danger"
        )

        return redirect(
            url_for("home.home")
        )

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

        try:

            current_password_valid = current_user.check_password(
                current_password
            )

        except Exception:

            current_app.logger.exception(
                "Current password verification failed for user %s.",
                current_user.id
            )

            current_password_valid = False

        if not current_password_valid:

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
        # Prevent same password
        # ----------------------------------------------------

        try:

            same_password = current_user.check_password(
                new_password
            )

        except Exception:

            current_app.logger.exception(
                "New password comparison failed for user %s.",
                current_user.id
            )

            same_password = False

        if same_password:

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

        except SQLAlchemyError:

            db.session.rollback()

            current_app.logger.exception(
                "Database error while changing password for user %s.",
                current_user.id
            )

            flash(
                "Unable to change your password right now. "
                "Please try again.",
                "danger"
            )

        except Exception:

            db.session.rollback()

            current_app.logger.exception(
                "Unexpected error while changing password for user %s.",
                current_user.id
            )

            flash(
                "Unable to change your password right now. "
                "Please try again.",
                "danger"
            )

    return render_template(
        "admin/change_password.html"
    )