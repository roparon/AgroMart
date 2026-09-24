from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.order import Order
from app.services.email_service import send_email


orders_bp = Blueprint("orders", __name__)


ORDER_STATUSES = [
    "Pending",
    "Confirmed",
    "Processing",
    "Shipped",
    "Delivered",
    "Cancelled",
]


# ============================================================
# ADMIN ACCESS
# ============================================================

def admin_required():
    """
    Allow access only to authenticated administrators.
    """

    if not current_user.is_authenticated or not current_user.is_admin:
        flash(
            "You do not have permission to access this page.",
            "danger",
        )
        return False

    return True


# ============================================================
# ORDER LIST
# ============================================================

@orders_bp.route("/")
@login_required
def orders():

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        orders = (
            Order.query
            .order_by(
                Order.created_at.desc()
            )
            .all()
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load admin orders."
        )

        flash(
            "Unable to load orders right now. Please try again.",
            "danger",
        )

        return render_template(
            "admin/orders.html",
            orders=[],
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while loading admin orders."
        )

        flash(
            "Unable to load orders right now. Please try again.",
            "danger",
        )

        return render_template(
            "admin/orders.html",
            orders=[],
        )

    return render_template(
        "admin/orders.html",
        orders=orders,
    )


# ============================================================
# ORDER DETAIL
# ============================================================

@orders_bp.route("/<int:order_id>")
@login_required
def order_detail(order_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        order = Order.query.get(
            order_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load order %s.",
            order_id,
        )

        flash(
            "Unable to load the order right now.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while loading order %s.",
            order_id,
        )

        flash(
            "Unable to load the order right now.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    if order is None:
        flash(
            "Order not found.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    return render_template(
        "admin/order_detail.html",
        order=order,
        order_statuses=ORDER_STATUSES,
    )


# ============================================================
# UPDATE ORDER STATUS
# ============================================================

@orders_bp.route(
    "/<int:order_id>/status",
    methods=["POST"],
)
@login_required
def update_order_status(order_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        order = Order.query.get(
            order_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load order %s for status update.",
            order_id,
        )

        flash(
            "Unable to load the order right now.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while loading order %s "
            "for status update.",
            order_id,
        )

        flash(
            "Unable to load the order right now.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    if order is None:
        flash(
            "Order not found.",
            "danger",
        )

        return redirect(
            url_for("orders.orders")
        )

    new_status = (
        request.form.get(
            "status",
            "",
        )
        .strip()
    )

    if new_status not in ORDER_STATUSES:
        flash(
            "Invalid order status.",
            "danger",
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    old_status = order.status

    if old_status == new_status:
        flash(
            "The order status is already set to this value.",
            "info",
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    # --------------------------------------------------------
    # Update database
    # --------------------------------------------------------

    try:
        order.status = new_status

        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while updating order %s status "
            "from %s to %s.",
            order_id,
            old_status,
            new_status,
        )

        flash(
            "Unable to update the order status. Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while updating order %s status "
            "from %s to %s.",
            order_id,
            old_status,
            new_status,
        )

        flash(
            "Unable to update the order status. Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "orders.order_detail",
                order_id=order.id,
            )
        )

    # --------------------------------------------------------
    # Email notification
    # --------------------------------------------------------
    #
    # The database update has already succeeded. Email is
    # non-critical, so an email failure must NOT roll back or
    # falsely report the status update as unsuccessful.
    # --------------------------------------------------------

    try:
        recipient_email = (
            order.user.email
            if order.user
            else None
        )

        if recipient_email:
            send_email(
                subject=(
                    f"AgroMart Order Update - "
                    f"{order.order_code}"
                ),
                recipients=[recipient_email],
                template="emails/order_status_update.html",
                order=order,
                old_status=old_status,
                new_status=new_status,
            )

        else:
            current_app.logger.warning(
                "Order %s has no associated customer email; "
                "status notification was not sent.",
                order_id,
            )

    except Exception:
        current_app.logger.exception(
            "Order %s status was updated successfully, "
            "but the notification email could not be sent.",
            order_id,
        )

    flash(
        f"Order {order.order_code} status updated to {new_status}.",
        "success",
    )

    return redirect(
        url_for(
            "orders.order_detail",
            order_id=order.id,
        )
    )