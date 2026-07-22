    

from app import db
from flask import Blueprint, render_template, redirect, url_for, flash

from app.models.product import Product

admin_bp = Blueprint(
    "admin",
    __name__,
)



@admin_bp.route("/products")
# @login_required
def products():

    # admin_required()

    products = Product.query.order_by(
        Product.created_at.desc()
    ).all()

    return render_template(
        "admin/products.html",
        products=products,
    )


@admin_bp.route("/products/add")
# @login_required
def add_product():

    # admin_required()

    return "<h1>Add Product - Coming Soon</h1>"


@admin_bp.route("/products/<int:product_id>/edit")
# @login_required
def edit_product(product_id):

    # admin_required()

    product = Product.query.get_or_404(product_id)

    return (
        f"<h1>Edit Product: "
        f"{product.name}</h1>"
    )


@admin_bp.route("/products/<int:product_id>/delete")
# @login_required
def delete_product(product_id):

    # admin_required()

    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    flash(
        "Product deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.products")
    )

