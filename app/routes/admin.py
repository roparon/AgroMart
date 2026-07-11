from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@login_required
def dashboard():

    if current_user.role != "admin":
        abort(403)

    return render_template("admin/dashboard.html")