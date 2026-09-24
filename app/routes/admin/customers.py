from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.user import User


customers_bp = Blueprint("customers", __name__)


# ============================================================
# ADMIN ACCESS
# ============================================================

def admin_required():
    """
    Allow access only to authenticated administrators.
    """

    if not current_user.is_authenticated or not current_user.is_admin:
        flash(
            "You do not have permission to access the admin area.",
            "danger",
        )
        return False

    return True


# ============================================================
# CUSTOMER LIST
# ============================================================

@customers_bp.route("/customers")
@login_required
def customers():

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        customers = (
            User.query
            .order_by(
                User.created_at.desc()
            )
            .all()
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load admin customer list."
        )

        flash(
            "Unable to load customers right now. Please try again.",
            "danger",
        )

        return render_template(
            "admin/customers.html",
            customers=[],
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while loading admin customer list."
        )

        flash(
            "Unable to load customers right now. Please try again.",
            "danger",
        )

        return render_template(
            "admin/customers.html",
            customers=[],
        )

    return render_template(
        "admin/customers.html",
        customers=customers,
    )


# ============================================================
# CUSTOMER DETAIL
# ============================================================

@customers_bp.route("/customers/<int:user_id>")
@login_required
def customer_detail(user_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        customer = User.query.get(
            user_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load customer %s.",
            user_id,
        )

        flash(
            "Unable to load the customer right now.",
            "danger",
        )

        return redirect(
            url_for("customers.customers")
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while loading customer %s.",
            user_id,
        )

        flash(
            "Unable to load the customer right now.",
            "danger",
        )

        return redirect(
            url_for("customers.customers")
        )

    if customer is None:
        flash(
            "Customer not found.",
            "danger",
        )

        return redirect(
            url_for("customers.customers")
        )

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
    )