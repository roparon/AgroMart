from flask import Blueprint, render_template
from app.models.product import Product


product_bp = Blueprint("product", __name__)


@product_bp.route("/")
def products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("product.html", products=products)


@product_bp.route("/<int:id>")
def product_details(id):

    product = Product.query.get_or_404(id)
    return render_template(
        "product_details.html",
        product=product)