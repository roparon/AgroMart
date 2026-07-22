
from flask import Blueprint, render_template
from app.models.user import User
admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/customers")
# @login_required
def customers():

    # admin_required()

    customers = User.query.order_by(
        User.created_at.desc()
    ).all()

    return render_template(
        "admin/customers.html",
        customers=customers,
    )


@admin_bp.route(
    "/customers/<int:user_id>"
)
# @login_required
def customer_detail(user_id):

    # admin_required()

    customer = User.query.get_or_404(
        user_id
    )

    return render_template(
        "admin/customer_detail.html",
        customer=customer,
    )