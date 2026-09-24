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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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

    try:
        image.stream.seek(0, os.SEEK_END)
        file_size = image.stream.tell()
        image.stream.seek(0)
    except (OSError, ValueError):
        raise ValueError(
            "Unable to read the uploaded category image."
        )

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

    try:
        os.makedirs(
            upload_folder,
            exist_ok=True,
        )
    except OSError:
        current_app.logger.exception(
            "Failed to create category image upload directory."
        )
        raise ValueError(
            "Unable to prepare category image storage."
        )

    # --------------------------------------------------------
    # Generate unique filename
    # --------------------------------------------------------

    original_filename = secure_filename(
        image.filename
    )

    if not original_filename or "." not in original_filename:
        raise ValueError(
            "The uploaded category image has an invalid filename."
        )

    extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    filename = f"{uuid.uuid4().hex}.{extension}"

    filepath = os.path.join(
        upload_folder,
        filename,
    )

    try:
        image.save(filepath)
    except (OSError, ValueError):
        current_app.logger.exception(
            "Failed to save category image."
        )

        # Best-effort cleanup in case a partial file was created.
        try:
            if os.path.isfile(filepath):
                os.remove(filepath)
        except OSError:
            current_app.logger.exception(
                "Failed to clean up partially saved category image."
            )

        raise ValueError(
            "Unable to save the category image."
        )

    # Store path relative to /static
    return f"uploads/categories/{filename}"


def delete_category_image(image_url):
    """
    Delete an existing category image from disk.

    Filesystem cleanup is intentionally best-effort so that an
    image deletion failure does not crash an otherwise successful
    database operation.
    """

    if not image_url:
        return

    try:
        filepath = os.path.join(
            current_app.static_folder,
            image_url,
        )

        # Prevent accidental deletion outside static/.
        static_folder = os.path.abspath(
            current_app.static_folder
        )
        absolute_filepath = os.path.abspath(filepath)

        if not (
            absolute_filepath == static_folder
            or absolute_filepath.startswith(
                static_folder + os.sep
            )
        ):
            current_app.logger.warning(
                "Refused to delete category image outside static folder: %s",
                image_url,
            )
            return

        if os.path.isfile(absolute_filepath):
            try:
                os.remove(absolute_filepath)
            except OSError:
                current_app.logger.exception(
                    "Failed to delete category image: %s",
                    image_url,
                )

    except (OSError, TypeError, ValueError):
        current_app.logger.exception(
            "Unexpected error while deleting category image: %s",
            image_url,
        )


# ============================================================
# CATEGORY LIST
# ============================================================

@categories_bp.route("/")
@login_required
def categories():

    if not admin_required():
        return redirect(url_for("home.home"))

    try:
        categories = (
            Category.query
            .order_by(
                Category.created_at.desc(),
                Category.id.desc(),
            )
            .all()
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load admin categories."
        )

        flash(
            "Unable to load categories right now. Please try again.",
            "danger",
        )

        return render_template(
            "admin/categories.html",
            categories=[],
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

        name = (
            form.name.data.strip()
            if form.name.data
            else ""
        )

        slug = (
            form.slug.data.strip().lower()
            if form.slug.data
            else ""
        )

        # ----------------------------------------------------
        # Check duplicate category name
        # ----------------------------------------------------

        try:
            existing_name = Category.query.filter(
                db.func.lower(Category.name) == name.lower()
            ).first()

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Failed to check duplicate category name."
            )

            flash(
                "Unable to validate the category name right now.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

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

        try:
            existing_slug = Category.query.filter(
                db.func.lower(Category.slug) == slug.lower()
            ).first()

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Failed to check duplicate category slug."
            )

            flash(
                "Unable to validate the category slug right now.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

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

        except IntegrityError:
            db.session.rollback()

            # A duplicate may still occur after the pre-check
            # because another request could create the same
            # category concurrently.
            if image_url:
                delete_category_image(image_url)

            current_app.logger.warning(
                "Category creation failed due to a database "
                "integrity constraint."
            )

            flash(
                "A category with this name or slug already exists.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        except SQLAlchemyError:
            db.session.rollback()

            if image_url:
                delete_category_image(image_url)

            current_app.logger.exception(
                "Database error while creating category."
            )

            flash(
                "An error occurred while creating the category.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Add Category",
            )

        except Exception:
            db.session.rollback()

            if image_url:
                delete_category_image(image_url)

            current_app.logger.exception(
                "Unexpected error while creating category."
            )

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

    try:
        category = Category.query.get(
            category_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load category %s for editing.",
            category_id,
        )

        flash(
            "Unable to load the category right now.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    if category is None:
        flash(
            "Category not found.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    form = CategoryForm(
        obj=category
    )

    if form.validate_on_submit():

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        name = (
            form.name.data.strip()
            if form.name.data
            else ""
        )

        slug = (
            form.slug.data.strip().lower()
            if form.slug.data
            else ""
        )

        # ----------------------------------------------------
        # Check duplicate name
        # ----------------------------------------------------

        try:
            existing_name = Category.query.filter(
                db.func.lower(Category.name) == name.lower(),
                Category.id != category.id,
            ).first()

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Failed to check duplicate category name "
                "while editing category %s.",
                category_id,
            )

            flash(
                "Unable to validate the category name right now.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
                category=category,
            )

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

        try:
            existing_slug = Category.query.filter(
                db.func.lower(Category.slug) == slug.lower(),
                Category.id != category.id,
            ).first()

        except SQLAlchemyError:
            db.session.rollback()

            current_app.logger.exception(
                "Failed to check duplicate category slug "
                "while editing category %s.",
                category_id,
            )

            flash(
                "Unable to validate the category slug right now.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
                category=category,
            )

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

        except IntegrityError:
            db.session.rollback()

            # Remove replacement image because the database
            # update did not succeed.
            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_category_image(
                    new_image_url
                )

            current_app.logger.warning(
                "Category update failed due to a database "
                "integrity constraint for category %s.",
                category_id,
            )

            flash(
                "Another category already uses this name or slug.",
                "danger",
            )

            return render_template(
                "admin/category_form.html",
                form=form,
                title="Edit Category",
                category=category,
            )

        except SQLAlchemyError:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_category_image(
                    new_image_url
                )

            current_app.logger.exception(
                "Database error while updating category %s.",
                category_id,
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

        except Exception:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_category_image(
                    new_image_url
                )

            current_app.logger.exception(
                "Unexpected error while updating category %s.",
                category_id,
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

    try:
        category = Category.query.get(
            category_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load category %s for deletion.",
            category_id,
        )

        flash(
            "Unable to load the category right now.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    if category is None:
        flash(
            "Category not found.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    # --------------------------------------------------------
    # Prevent deleting categories containing products
    # --------------------------------------------------------

    try:
        has_products = bool(category.products)

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to check products for category %s.",
            category_id,
        )

        flash(
            "Unable to verify whether the category can be deleted.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    if has_products:

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

    except IntegrityError:
        db.session.rollback()

        current_app.logger.warning(
            "Category deletion failed due to an integrity "
            "constraint for category %s.",
            category_id,
        )

        flash(
            "Cannot delete this category because it is still "
            "being used by other records.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while deleting category %s.",
            category_id,
        )

        flash(
            "An error occurred while deleting the category.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while deleting category %s.",
            category_id,
        )

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

    try:
        category = Category.query.get(
            category_id
        )

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to load category %s for status toggle.",
            category_id,
        )

        flash(
            "Unable to load the category right now.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    if category is None:
        flash(
            "Category not found.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    category.is_active = not category.is_active

    try:
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()

        current_app.logger.exception(
            "Database error while updating category status %s.",
            category_id,
        )

        flash(
            "Unable to update category status.",
            "danger",
        )

        return redirect(
            url_for("admin_categories.categories")
        )

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unexpected error while updating category status %s.",
            category_id,
        )

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