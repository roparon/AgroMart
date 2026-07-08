from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/")
def dashboard():
    return "<h1>AgroMart Admin Dashboard</h1>"