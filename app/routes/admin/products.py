from flask import Blueprint, render_template, redirect, url_for, flash

from app import db
from app.models.product import Product


products_bp = Blueprint(
    "admin_products",
    __name__,
)


# ============================================================
# PRODUCT MANAGEMENT
# ============================================================

@products_bp.route("/")
def products():

    products = Product.query.order_by(
        Product.created_at.desc()
    ).all()

    return render_template(
        "admin/products.html",
        products=products,
    )


# ============================================================
# ADD PRODUCT
# ============================================================

@products_bp.route("/add")
def add_product():

    return "<h1>Add Product - Coming Soon</h1>"


# ============================================================
# EDIT PRODUCT
# ============================================================

@products_bp.route("/<int:product_id>/edit")
def edit_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    return (
        f"<h1>Edit Product: "
        f"{product.name}</h1>"
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

@products_bp.route(
    "/<int:product_id>/delete",
    methods=["POST"]
)
def delete_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    db.session.delete(product)
    db.session.commit()

    flash(
        "Product deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin_products.products")
    )