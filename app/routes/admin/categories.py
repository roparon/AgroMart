from flask import Blueprint, render_template, flash, redirect, url_for
from app.forms.category_forms import CategoryForm
from app.models.category import Category
from app import db

categories_bp = Blueprint(
    "categories",
    __name__,
)




@categories_bp.route("/categories")
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


@categories_bp.route(
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


@categories_bp.route(
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


@categories_bp.route(
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


@categories_bp.route(
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
