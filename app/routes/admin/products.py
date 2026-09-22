import uuid

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
)

from flask_login import login_required

from vercel.blob import BlobClient

from werkzeug.utils import secure_filename

from app import db

from app.forms.product_forms import ProductForm

from app.models.product import Product
from app.models.category import Category
from app.models.product_image import ProductImage


# ============================================================
# BLUEPRINT
# ============================================================

products_bp = Blueprint(
    "admin_products",
    __name__,
)


# ============================================================
# IMAGE CONFIGURATION
# ============================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

MAX_IMAGE_SIZE = 4 * 1024 * 1024

BLOB_PRODUCT_FOLDER = "products"


# ============================================================
# IMAGE VALIDATION
# ============================================================

def allowed_image(filename):
    """
    Check whether an uploaded filename has an allowed extension.
    """

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1,
    )[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


def validate_image_size(image):
    """
    Validate the uploaded image size.

    Uses the file stream directly so we do not need to load
    the complete image into memory just for validation.
    """

    if not image:
        return False

    try:
        current_position = image.tell()

        image.seek(
            0,
            2,
        )

        file_size = image.tell()

        image.seek(
            current_position,
        )

    except (OSError, AttributeError):
        return True

    if file_size <= 0:
        raise ValueError(
            "The uploaded image is empty."
        )

    if file_size > MAX_IMAGE_SIZE:
        raise ValueError(
            "Image size must not exceed 4 MB."
        )

    return True


# ============================================================
# VERCEL BLOB CLIENT
# ============================================================

def _get_blob_client():
    """
    Create a Vercel Blob client.

    Vercel automatically provides the Blob token in the
    production environment when the Blob store is connected
    correctly to the project.
    """

    return BlobClient()


# ============================================================
# UPLOAD PRODUCT IMAGE
# ============================================================

def upload_product_image(image):
    """
    Upload a product image to Vercel Blob.

    Returns:
        str | None:
            Public Blob URL.

    Raises:
        ValueError:
            For invalid image files.
        RuntimeError:
            When Blob upload does not return a URL.
    """

    if not image or not image.filename:
        return None

    # --------------------------------------------------------
    # SECURE ORIGINAL FILENAME
    # --------------------------------------------------------

    original_filename = secure_filename(
        image.filename
    )

    if not original_filename:
        raise ValueError(
            "Invalid image filename."
        )

    # --------------------------------------------------------
    # VALIDATE EXTENSION
    # --------------------------------------------------------

    if not allowed_image(
        original_filename
    ):
        raise ValueError(
            "Unsupported image format. "
            "Allowed formats: JPG, JPEG, PNG and WEBP."
        )

    extension = original_filename.rsplit(
        ".",
        1,
    )[1].lower()

    # --------------------------------------------------------
    # VALIDATE SIZE
    # --------------------------------------------------------

    validate_image_size(
        image
    )

    # --------------------------------------------------------
    # READ IMAGE DATA
    # --------------------------------------------------------

    image.seek(0)

    image_data = image.read()

    if not image_data:
        raise ValueError(
            "The uploaded image is empty."
        )

    # --------------------------------------------------------
    # GENERATE UNIQUE BLOB NAME
    # --------------------------------------------------------

    unique_filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    blob_path = (
        f"{BLOB_PRODUCT_FOLDER}/"
        f"{unique_filename}"
    )

    # --------------------------------------------------------
    # UPLOAD TO VERCEL BLOB
    # --------------------------------------------------------

    client = _get_blob_client()

    uploaded = client.put(
        blob_path,
        image_data,
        access="public",
        content_type=(
            image.mimetype
            or "application/octet-stream"
        ),
        add_random_suffix=False,
    )

    # --------------------------------------------------------
    # GET PUBLIC URL
    # --------------------------------------------------------

    image_url = getattr(
        uploaded,
        "url",
        None,
    )

    # Defensive support in case the SDK returns a dictionary.
    if not image_url and isinstance(
        uploaded,
        dict,
    ):
        image_url = uploaded.get(
            "url"
        )

    if not image_url:
        raise RuntimeError(
            "Vercel Blob upload succeeded but "
            "no public image URL was returned."
        )

    return image_url


# ============================================================
# DELETE PRODUCT IMAGE FROM VERCEL BLOB
# ============================================================

def delete_product_image_file(image_url):
    """
    Delete an image from Vercel Blob.

    Important:
    Older images using local URLs such as:

        /static/uploads/products/...

    are intentionally left untouched.

    Only Vercel Blob URLs are sent to the Blob API.
    """

    if not image_url:
        return

    # --------------------------------------------------------
    # ONLY DELETE VERCEL BLOB OBJECTS
    # --------------------------------------------------------

    if "blob.vercel-storage.com" not in image_url:
        return

    try:

        client = _get_blob_client()

        client.delete(
            image_url
        )

    except Exception as exc:

        # Blob deletion failure should never prevent the
        # database operation from completing.
        print(
            "Warning: could not delete "
            f"Vercel Blob image: {exc}"
        )


# ============================================================
# PRODUCT LIST
# ============================================================

@products_bp.route("/")
@login_required
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

@products_bp.route(
    "/add",
    methods=["GET", "POST"],
)
@login_required
def add_product():

    form = ProductForm()

    # --------------------------------------------------------
    # LOAD ACTIVE CATEGORIES
    # --------------------------------------------------------

    categories = Category.query.filter_by(
        is_active=True
    ).order_by(
        Category.name.asc()
    ).all()

    form.category.choices = [
        (
            category.id,
            category.name,
        )
        for category in categories
    ]

    # --------------------------------------------------------
    # VALIDATE FORM
    # --------------------------------------------------------

    if form.validate_on_submit():

        # ----------------------------------------------------
        # CHECK DUPLICATE SLUG
        # ----------------------------------------------------

        if form.slug.data:

            existing_slug = Product.query.filter_by(
                slug=form.slug.data
            ).first()

            if existing_slug:

                flash(
                    "A product with this slug already exists.",
                    "danger",
                )

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Add Product",
                )

        # ----------------------------------------------------
        # CREATE PRODUCT
        # ----------------------------------------------------

        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            description=form.description.data,
            price=form.price.data,
            discount=form.discount.data or 0,
            stock=form.stock.data,
            slug=form.slug.data,
            category_id=form.category.data,
            featured=form.featured.data,
            is_active=form.is_active.data,
        )

        db.session.add(
            product
        )

        # ----------------------------------------------------
        # FLUSH
        #
        # Gives product its database ID before images are
        # inserted.
        # ----------------------------------------------------

        db.session.flush()

        # ----------------------------------------------------
        # GENERATE SKU
        # ----------------------------------------------------

        product.sku = (
            f"BM-{product.id:06d}"
        )

        # ----------------------------------------------------
        # GET UPLOADED IMAGES
        # ----------------------------------------------------

        uploaded_images = request.files.getlist(
            "images"
        )

        image_number = 0

        try:

            for image in uploaded_images:

                if not image or not image.filename:
                    continue

                # --------------------------------------------
                # VALIDATE IMAGE TYPE
                # --------------------------------------------

                if not allowed_image(
                    image.filename
                ):

                    raise ValueError(
                        f"Invalid image format: "
                        f"{image.filename}"
                    )

                # --------------------------------------------
                # UPLOAD TO VERCEL BLOB
                # --------------------------------------------

                image_url = upload_product_image(
                    image
                )

                if not image_url:
                    continue

                # --------------------------------------------
                # CREATE IMAGE DATABASE RECORD
                # --------------------------------------------

                product_image = ProductImage(
                    image_url=image_url,
                    product_id=product.id,
                    is_primary=(
                        image_number == 0
                    ),
                )

                db.session.add(
                    product_image
                )

                image_number += 1

        except Exception as exc:

            db.session.rollback()

            print(
                "Product image upload failed: "
                f"{exc}"
            )

            flash(
                "The product could not be created because "
                "the image upload failed. Please check the "
                "image format and size and try again.",
                "danger",
            )

            return render_template(
                "admin/product_form.html",
                form=form,
                title="Add Product",
            )

        # ----------------------------------------------------
        # COMMIT PRODUCT + IMAGES
        # ----------------------------------------------------

        try:

            db.session.commit()

        except Exception as exc:

            db.session.rollback()

            print(
                "Product database commit failed: "
                f"{exc}"
            )

            flash(
                "The product could not be saved. "
                "Please try again.",
                "danger",
            )

            return render_template(
                "admin/product_form.html",
                form=form,
                title="Add Product",
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash(
            f"Product created successfully. "
            f"SKU: {product.sku}",
            "success",
        )

        return redirect(
            url_for(
                "admin_products.products"
            )
        )

    # --------------------------------------------------------
    # DISPLAY FORM
    # --------------------------------------------------------

    return render_template(
        "admin/product_form.html",
        form=form,
        title="Add Product",
    )


# ============================================================
# EDIT PRODUCT
# ============================================================

@products_bp.route(
    "/<int:product_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    form = ProductForm(
        obj=product
    )

    # --------------------------------------------------------
    # LOAD ACTIVE CATEGORIES
    # --------------------------------------------------------

    categories = Category.query.filter_by(
        is_active=True
    ).order_by(
        Category.name.asc()
    ).all()

    form.category.choices = [
        (
            category.id,
            category.name,
        )
        for category in categories
    ]

    # --------------------------------------------------------
    # SET INITIAL FORM VALUES
    # --------------------------------------------------------

    if not form.is_submitted():

        form.category.data = (
            product.category_id
        )

        form.featured.data = (
            product.featured
        )

        form.is_active.data = (
            product.is_active
        )

    # --------------------------------------------------------
    # PROCESS UPDATE
    # --------------------------------------------------------

    if form.validate_on_submit():

        # ----------------------------------------------------
        # CHECK DUPLICATE SKU
        # ----------------------------------------------------

        if form.sku.data:

            existing_sku = Product.query.filter(
                Product.sku == form.sku.data,
                Product.id != product.id,
            ).first()

            if existing_sku:

                flash(
                    "Another product already uses this SKU.",
                    "danger",
                )

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Edit Product",
                    product=product,
                )

        # ----------------------------------------------------
        # CHECK DUPLICATE SLUG
        # ----------------------------------------------------

        if form.slug.data:

            existing_slug = Product.query.filter(
                Product.slug == form.slug.data,
                Product.id != product.id,
            ).first()

            if existing_slug:

                flash(
                    "Another product already uses this slug.",
                    "danger",
                )

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Edit Product",
                    product=product,
                )

        # ----------------------------------------------------
        # UPDATE PRODUCT FIELDS
        # ----------------------------------------------------

        product.name = form.name.data
        product.brand = form.brand.data
        product.description = form.description.data
        product.price = form.price.data
        product.discount = form.discount.data or 0
        product.stock = form.stock.data
        product.slug = form.slug.data
        product.category_id = form.category.data
        product.featured = form.featured.data
        product.is_active = form.is_active.data

        # ----------------------------------------------------
        # GET NEW IMAGES
        # ----------------------------------------------------

        uploaded_images = request.files.getlist(
            "images"
        )

        existing_images = ProductImage.query.filter_by(
            product_id=product.id
        ).count()

        image_number = existing_images

        try:

            for image in uploaded_images:

                if not image or not image.filename:
                    continue

                # --------------------------------------------
                # VALIDATE TYPE
                # --------------------------------------------

                if not allowed_image(
                    image.filename
                ):

                    raise ValueError(
                        f"Invalid image format: "
                        f"{image.filename}"
                    )

                # --------------------------------------------
                # UPLOAD TO VERCEL BLOB
                # --------------------------------------------

                image_url = upload_product_image(
                    image
                )

                if not image_url:
                    continue

                # --------------------------------------------
                # CREATE DATABASE RECORD
                # --------------------------------------------

                product_image = ProductImage(
                    image_url=image_url,
                    product_id=product.id,
                    is_primary=(
                        image_number == 0
                    ),
                )

                db.session.add(
                    product_image
                )

                image_number += 1

        except Exception as exc:

            db.session.rollback()

            print(
                "Product image upload failed: "
                f"{exc}"
            )

            flash(
                "The product could not be updated because "
                "the image upload failed. Please check the "
                "image format and size and try again.",
                "danger",
            )

            return render_template(
                "admin/product_form.html",
                form=form,
                title="Edit Product",
                product=product,
            )

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        try:

            db.session.commit()

        except Exception as exc:

            db.session.rollback()

            print(
                "Product database update failed: "
                f"{exc}"
            )

            flash(
                "The product could not be updated. "
                "Please try again.",
                "danger",
            )

            return render_template(
                "admin/product_form.html",
                form=form,
                title="Edit Product",
                product=product,
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash(
            "Product updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "admin_products.products"
            )
        )

    # --------------------------------------------------------
    # DISPLAY FORM
    # --------------------------------------------------------

    return render_template(
        "admin/product_form.html",
        form=form,
        title="Edit Product",
        product=product,
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

@products_bp.route(
    "/<int:product_id>/delete",
    methods=["POST"],
)
@login_required
def delete_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    # --------------------------------------------------------
    # COLLECT IMAGE URLS
    # --------------------------------------------------------

    image_urls = [
        image.image_url
        for image in product.images
        if image.image_url
    ]

    # --------------------------------------------------------
    # DELETE PRODUCT FROM DATABASE
    #
    # Blob deletion is deliberately performed after the
    # database operation so a Blob problem does not prevent
    # product deletion.
    # --------------------------------------------------------

    db.session.delete(
        product
    )

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        print(
            "Product deletion failed: "
            f"{exc}"
        )

        flash(
            "The product could not be deleted. "
            "Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "admin_products.products"
            )
        )

    # --------------------------------------------------------
    # CLEAN UP BLOB IMAGES
    # --------------------------------------------------------

    for image_url in image_urls:

        delete_product_image_file(
            image_url
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    flash(
        "Product deleted successfully.",
        "success",
    )

    return redirect(
        url_for(
            "admin_products.products"
        )
    )


# ============================================================
# DELETE PRODUCT IMAGE
# ============================================================

@products_bp.route(
    "/image/<int:image_id>/delete",
    methods=["POST"],
)
@login_required
def delete_product_image(image_id):

    image = ProductImage.query.get_or_404(
        image_id
    )

    product_id = image.product_id
    image_url = image.image_url
    was_primary = image.is_primary

    # --------------------------------------------------------
    # DELETE DATABASE RECORD
    # --------------------------------------------------------

    db.session.delete(
        image
    )
    

    db.session.flush()

    # --------------------------------------------------------
    # IF PRIMARY IMAGE WAS DELETED,
    # SELECT ANOTHER IMAGE
    # --------------------------------------------------------

    if was_primary:

        replacement = ProductImage.query.filter_by(
            product_id=product_id
        ).order_by(
            ProductImage.id.asc()
        ).first()

        if replacement:

            replacement.is_primary = True

    # --------------------------------------------------------
    # COMMIT DATABASE CHANGE
    # --------------------------------------------------------

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        print(
            "Product image database deletion failed: "
            f"{exc}"
        )

        flash(
            "The product image could not be deleted. "
            "Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "admin_products.edit_product",
                product_id=product_id,
            )
        )

    # --------------------------------------------------------
    # DELETE BLOB AFTER DATABASE SUCCESS
    # --------------------------------------------------------

    delete_product_image_file(
        image_url
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    flash(
        "Product image deleted successfully.",
        "success",
    )

    return redirect(
        url_for(
            "admin_products.edit_product",
            product_id=product_id,
        )
    )


# ============================================================
# SET PRIMARY PRODUCT IMAGE
# ============================================================

@products_bp.route(
    "/image/<int:image_id>/primary",
    methods=["POST"],
)
@login_required
def set_primary_image(image_id):

    image = ProductImage.query.get_or_404(
        image_id
    )

    product_id = image.product_id

    # --------------------------------------------------------
    # REMOVE PRIMARY STATUS FROM ALL IMAGES
    # --------------------------------------------------------

    ProductImage.query.filter_by(
        product_id=product_id
    ).update(
        {
            ProductImage.is_primary: False
        }
    )

    # --------------------------------------------------------
    # SET SELECTED IMAGE AS PRIMARY
    # --------------------------------------------------------

    image.is_primary = True

    try:

        db.session.commit()

    except Exception as exc:

        db.session.rollback()

        print(
            "Primary image update failed: "
            f"{exc}"
        )

        flash(
            "The primary image could not be updated. "
            "Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "admin_products.edit_product",
                product_id=product_id,
            )
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    flash(
        "Primary product image updated.",
        "success",
    )

    return redirect(
        url_for(
            "admin_products.edit_product",
            product_id=product_id,
        )
    )