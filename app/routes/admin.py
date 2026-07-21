from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
)

# We will enable these again when admin authentication is ready
# from flask_login import login_required, current_user

from app import db

from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.user import User

from app.forms.category_forms import CategoryForm


admin_bp = Blueprint(
    "admin",
    __name__,
)


# ============================================================
# ADMIN AUTHORIZATION
# ============================================================

# We will enable this when admin authentication is ready.
#
# def admin_required():
#     if not current_user.is_authenticated:
#         abort(401)
#
#     if current_user.role != "admin":
#         abort(403)


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/")
# @login_required
def dashboard():

    # admin_required()

    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()

    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_categories=total_categories,
        total_orders=total_orders,
        total_users=total_users,
    )


# ============================================================
# PRODUCT MANAGEMENT
# ============================================================

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


# ============================================================
# CATEGORY MANAGEMENT
# ============================================================

@admin_bp.route("/categories")
# @login_required
def categories():

    # admin_required()

    categories = Category.query.order_by(
        Category.created_at.desc()
    ).all()

    return render_template(
        "admin/categories.html",
        categories=categories,
    )


@admin_bp.route(
    "/categories/add",
    methods=["GET", "POST"],
)
# @login_required
def add_category():

    # admin_required()

    form = CategoryForm()

    if form.validate_on_submit():

        # Check duplicate category name
        existing_name = Category.query.filter_by(
            name=form.name.data
        ).first()

        if existing_name:

            flash(
                "A category with this name already exists.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        # Check duplicate slug
        existing_slug = Category.query.filter_by(
            slug=form.slug.data
        ).first()

        if existing_slug:

            flash(
                "A category with this slug already exists.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        # Create category
        category = Category(
            name=form.name.data,
            description=form.description.data,
            slug=form.slug.data,
            image_url=form.image_url.data,
            is_active=form.is_active.data,
        )

        db.session.add(category)
        db.session.commit()

        flash(
            "Category created successfully.",
            "success",
        )

        return redirect(
            url_for("admin.categories")
        )

    return render_template(
        "admin/category_form.html",
        form=form,
        title="Add Category",
    )


@admin_bp.route(
    "/categories/<int:category_id>/edit",
    methods=["GET", "POST"],
)
# @login_required
def edit_category(category_id):

    # admin_required()

    category = Category.query.get_or_404(
        category_id
    )

    form = CategoryForm(
        obj=category
    )

    if form.validate_on_submit():

        # Check if another category uses the same name
        existing_name = Category.query.filter(
            Category.name == form.name.data,
            Category.id != category.id,
        ).first()

        if existing_name:

            flash(
                "Another category already uses this name.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
            )

        # Check if another category uses the same slug
        existing_slug = Category.query.filter(
            Category.slug == form.slug.data,
            Category.id != category.id,
        ).first()

        if existing_slug:

            flash(
                "Another category already uses this slug.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
            )

        # Update category
        category.name = form.name.data
        category.description = form.description.data
        category.slug = form.slug.data
        category.image_url = form.image_url.data
        category.is_active = form.is_active.data

        db.session.commit()

        flash(
            "Category updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin.categories")
        )

    return render_template(
        "admin/category_form.html",
        form=form,
        title="Edit Category",
    )


@admin_bp.route(
    "/categories/<int:category_id>/delete",
    methods=["POST"],
)
# @login_required
def delete_category(category_id):

    # admin_required()

    category = Category.query.get_or_404(
        category_id
    )

    # Prevent deleting categories
    # that still contain products
    if category.products:

        flash(
            "Cannot delete this category because it contains products. "
            "Move or delete the products first.",
            "danger",
        )

        return redirect(
            url_for("admin.categories")
        )

    db.session.delete(category)
    db.session.commit()

    flash(
        "Category deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.categories")
    )


@admin_bp.route(
    "/categories/<int:category_id>/toggle-status",
    methods=["POST"],
)
# @login_required
def toggle_category_status(category_id):

    # admin_required()

    category = Category.query.get_or_404(
        category_id
    )

    category.is_active = not category.is_active

    db.session.commit()

    if category.is_active:

        flash(
            f"{category.name} has been activated.",
            "success",
        )

    else:

        flash(
            f"{category.name} has been deactivated.",
            "info",
        )

    return redirect(
        url_for("admin.categories")
    )


# ============================================================
# ORDER MANAGEMENT
# ============================================================

@admin_bp.route("/orders")
# @login_required
def orders():

    # admin_required()

    orders = Order.query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "admin/orders.html",
        orders=orders,
    )


@admin_bp.route(
    "/orders/<int:order_id>"
)
# @login_required
def order_detail(order_id):

    # admin_required()

    order = Order.query.get_or_404(
        order_id
    )

    return render_template(
        "admin/order_detail.html",
        order=order,
    )


# ============================================================
# CUSTOMER MANAGEMENT
# ============================================================

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