from flask import Blueprint, render_template

product_bp = Blueprint("product", __name__)

@product_bp.route("/")
def products():
    return render_template("product.html")

@product_bp.route("/<int:id>")
def product_details(id):
    return render_template("product_details.html")