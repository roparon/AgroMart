import os
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.forms.category_forms import CategoryForm
from app.models.category import Category


categories_bp = Blueprint(
    "admin_categories",
    __name__,
)


# ============================================================
# ADMIN ACCESS
# ============================================================

def admin_required():
    """
    Allow access only to authenticated administrators.
    """

    if not current_user.is_authenticated or not current_user.is_admin:
        flash(
            "You do not have permission to access the admin area.",
            "danger",
        )
        return False

    return True


# ============================================================
# IMAGE UPLOAD HELPERS
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024


def allowed_file(filename):
    """
    Check whether the uploaded file has an allowed extension.
    """

    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def save_category_image(image):
    """
    Save a category image and return its relative static path.
    """

    if not image or not image.filename:
        return None

    if not allowed_file(image.filename):
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    # --------------------------------------------------------
    # Check file size
    # --------------------------------------------------------

    image.stream.seek(0, os.SEEK_END)
    file_size = image.stream.tell()
    image.stream.seek(0)

    if file_size > MAX_IMAGE_SIZE:
        raise ValueError(
            "Category image must be smaller than 5 MB."
        )

    # --------------------------------------------------------
    # Create upload directory
    # --------------------------------------------------------

    upload_folder = os.path.join(
        current_app.static_folder,
        "uploads",
        "categories",
    )

    os.makedirs(
        upload_folder,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Generate unique filename
    # --------------------------------------------------------

    extension = (
        secure_filename(image.filename)
        .rsplit(".", 1)[1]
        .lower()
    )

    filename = f"{uuid.uuid4().hex}.{extension}"

    filepath = os.path.join(
        upload_folder,
        filename,
    )

    image.save(filepath)

    # Store path relative to /static
    return f"uploads/categories/{filename}"


def delete_category_image(image_url):
    """
    Delete an existing category image from disk.
    """

    if not image_url:
        return

    filepath = os.path.join(
        current_app.static_folder,
        image_url,
    )

    if os.path.isfile(filepath):
        try:
            os.remove(filepath)
        except OSError:
            pass


# ============================================================
# CATEGORY LIST
# ============================================================

@categories_bp.route("/")
@login_required
def categories():

    if not admin_required():
        return redirect(url_for("home.home"))

    categories = (
        Category.query
        .order_by(
            Category.created_at.desc(),
            Category.id.desc(),
        )
        .all()
    )

    return render_template(
        "admin/categories.html",
        categories=categories,
    )


# ============================================================
# ADD CATEGORY
# ============================================================

@categories_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
def add_category():

    if not admin_required():
        return redirect(url_for("home.home"))

    form = CategoryForm()

    if form.validate_on_submit():

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        name = form.name.data.strip()
        slug = form.slug.data.strip().lower()

        # ----------------------------------------------------
        # Check duplicate category name
        # ----------------------------------------------------

        existing_name = Category.query.filter(
            db.func.lower(Category.name) == name.lower()
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

        # ----------------------------------------------------
        # Check duplicate category slug
        # ----------------------------------------------------

        existing_slug = Category.query.filter(
            db.func.lower(Category.slug) == slug.lower()
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

        # ----------------------------------------------------
        # Handle image
        # ----------------------------------------------------

        image_url = None

        try:
            if form.image.data:
                image_url = save_category_image(
                    form.image.data
                )

        except ValueError as exc:
            flash(str(exc), "danger")

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        # ----------------------------------------------------
        # Create category
        # ----------------------------------------------------

        category = Category(
            name=name,
            description=(
                form.description.data.strip()
                if form.description.data
                else None
            ),
            slug=slug,
            image_url=image_url,
            is_active=form.is_active.data,
        )

        try:
            db.session.add(category)
            db.session.commit()

        except Exception:
            db.session.rollback()

            if image_url:
                delete_category_image(image_url)

            flash(
                "An error occurred while creating the category.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        flash(
            "Category created successfully.",
            "success",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    return render_template(
        "admin/category_form.html",
        form=form,
        title="Add Category",
    )


# ============================================================
# EDIT CATEGORY
# ============================================================

@categories_bp.route(
    "/<int:category_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_category(category_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    category = Category.query.get_or_404(
        category_id
    )

    form = CategoryForm(
        obj=category
    )

    if form.validate_on_submit():

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        name = form.name.data.strip()
        slug = form.slug.data.strip().lower()

        # ----------------------------------------------------
        # Check duplicate name
        # ----------------------------------------------------

        existing_name = Category.query.filter(
            db.func.lower(Category.name) == name.lower(),
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
                category=category,
            )

        # ----------------------------------------------------
        # Check duplicate slug
        # ----------------------------------------------------

        existing_slug = Category.query.filter(
            db.func.lower(Category.slug) == slug.lower(),
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
                category=category,
            )

        # ----------------------------------------------------
        # Keep old image until database update succeeds
        # ----------------------------------------------------

        old_image_url = category.image_url
        new_image_url = old_image_url

        # ----------------------------------------------------
        # Upload replacement image if provided
        # ----------------------------------------------------

        try:

            if form.image.data:
                new_image_url = save_category_image(
                    form.image.data
                )

        except ValueError as exc:
            flash(str(exc), "danger")

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
                category=category,
            )

        # ----------------------------------------------------
        # Update category
        # ----------------------------------------------------

        category.name = name

        category.description = (
            form.description.data.strip()
            if form.description.data
            else None
        )

        category.slug = slug
        category.image_url = new_image_url
        category.is_active = form.is_active.data

        try:
            db.session.commit()

        except Exception:
            db.session.rollback()

            # Remove newly uploaded image if DB update fails
            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_category_image(
                    new_image_url
                )

            flash(
                "An error occurred while updating the category.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
                category=category,
            )

        # ----------------------------------------------------
        # Remove old image after successful DB update
        # ----------------------------------------------------

        if (
            old_image_url
            and new_image_url != old_image_url
        ):
            delete_category_image(
                old_image_url
            )

        flash(
            "Category updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    return render_template(
        "admin/category_form.html",
        form=form,
        title="Edit Category",
        category=category,
    )


# ============================================================
# DELETE CATEGORY
# ============================================================

@categories_bp.route(
    "/<int:category_id>/delete",
    methods=["POST"],
)
@login_required
def delete_category(category_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    category = Category.query.get_or_404(
        category_id
    )

    # --------------------------------------------------------
    # Prevent deleting categories containing products
    # --------------------------------------------------------

    if category.products:

        flash(
            "Cannot delete this category because it contains "
            "products. Move or delete the products first.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    image_url = category.image_url

    try:
        db.session.delete(category)
        db.session.commit()

    except Exception:
        db.session.rollback()

        flash(
            "An error occurred while deleting the category.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    # --------------------------------------------------------
    # Delete image after successful DB deletion
    # --------------------------------------------------------

    if image_url:
        delete_category_image(image_url)

    flash(
        "Category deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin_categories.categories")
    )


# ============================================================
# TOGGLE CATEGORY STATUS
# ============================================================

@categories_bp.route(
    "/<int:category_id>/toggle-status",
    methods=["POST"],
)
@login_required
def toggle_category_status(category_id):

    if not admin_required():
        return redirect(url_for("home.home"))

    category = Category.query.get_or_404(
        category_id
    )

    category.is_active = not category.is_active

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        flash(
            "Unable to update category status.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

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
        url_for("admin_categories.categories")
    )