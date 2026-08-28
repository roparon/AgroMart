import os
import uuid

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    current_app,
    request,
)

from werkzeug.utils import secure_filename

from app import db

from app.forms.product_forms import ProductForm

from app.models.product import Product

from app.models.category import Category

from app.models.product_image import ProductImage


products_bp = Blueprint(
    "admin_products",
    __name__,
)


# ============================================================
# ALLOWED IMAGE TYPES
# ============================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}


def allowed_image(filename):
    """
    Check whether the uploaded file has an allowed extension.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


# ============================================================
# PRODUCT LIST
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

@products_bp.route(
    "/add",
    methods=["GET", "POST"],
)
def add_product():

    form = ProductForm()

    categories = Category.query.filter_by(
        is_active=True
    ).order_by(
        Category.name.asc()
    ).all()

    form.category.choices = [
        (category.id, category.name)
        for category in categories
    ]

    if form.validate_on_submit():

        # ----------------------------------------------------
        # CHECK SKU
        # ----------------------------------------------------

        if form.sku.data:

            existing_sku = Product.query.filter_by(
                sku=form.sku.data
            ).first()

            if existing_sku:

                flash(
                    "A product with this SKU already exists.",
                    "danger",
                )

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Add Product",
                )

        # ----------------------------------------------------
        # CHECK SLUG
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
            sku=form.sku.data,
            slug=form.slug.data,
            category_id=form.category.data,
            featured=form.featured.data,
            is_active=form.is_active.data,
        )

        db.session.add(product)

        # Flush so product.id is available before images
        db.session.flush()

        # ----------------------------------------------------
        # SAVE PRODUCT IMAGES
        # ----------------------------------------------------

        uploaded_images = request.files.getlist(
            "images"
        )

        upload_folder = current_app.config[
            "UPLOAD_FOLDER"
        ]

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        image_number = 0

        for image in uploaded_images:

            if not image or not image.filename:
                continue

            if not allowed_image(image.filename):

                flash(
                    f"Invalid image format: {image.filename}",
                    "danger",
                )

                db.session.rollback()

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Add Product",
                )

            # ------------------------------------------------
            # CREATE SAFE UNIQUE FILE NAME
            # ------------------------------------------------

            original_filename = secure_filename(
                image.filename
            )

            extension = original_filename.rsplit(
                ".",
                1
            )[1].lower()

            unique_filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            file_path = os.path.join(
                upload_folder,
                unique_filename,
            )

            # ------------------------------------------------
            # SAVE FILE
            # ------------------------------------------------

            image.save(file_path)

            # ------------------------------------------------
            # SAVE DATABASE RECORD
            # ------------------------------------------------

            product_image = ProductImage(
                image_url=(
                    f"/static/uploads/products/"
                    f"{unique_filename}"
                ),
                product_id=product.id,
                is_primary=(
                    image_number == 0
                ),
            )

            db.session.add(product_image)

            image_number += 1

        # ----------------------------------------------------
        # COMMIT PRODUCT + IMAGES
        # ----------------------------------------------------

        db.session.commit()

        flash(
            "Product created successfully.",
            "success",
        )

        return redirect(
            url_for(
                "admin_products.products"
            )
        )

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
def edit_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    form = ProductForm(
        obj=product
    )

    categories = Category.query.filter_by(
        is_active=True
    ).order_by(
        Category.name.asc()
    ).all()

    form.category.choices = [
        (category.id, category.name)
        for category in categories
    ]

    if not form.is_submitted():

        form.category.data = product.category_id

        form.featured.data = product.featured

        form.is_active.data = product.is_active

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
                )

        # ----------------------------------------------------
        # UPDATE PRODUCT
        # ----------------------------------------------------

        product.name = form.name.data
        product.brand = form.brand.data
        product.description = form.description.data
        product.price = form.price.data
        product.discount = form.discount.data or 0
        product.stock = form.stock.data
        product.sku = form.sku.data
        product.slug = form.slug.data
        product.category_id = form.category.data
        product.featured = form.featured.data
        product.is_active = form.is_active.data

        # ----------------------------------------------------
        # SAVE NEW IMAGES
        # ----------------------------------------------------

        uploaded_images = request.files.getlist(
            "images"
        )

        upload_folder = current_app.config[
            "UPLOAD_FOLDER"
        ]

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        existing_images = ProductImage.query.filter_by(
            product_id=product.id
        ).count()

        image_number = existing_images

        for image in uploaded_images:

            if not image or not image.filename:
                continue

            if not allowed_image(image.filename):

                flash(
                    f"Invalid image format: {image.filename}",
                    "danger",
                )

                db.session.rollback()

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Edit Product",
                )

            original_filename = secure_filename(
                image.filename
            )

            extension = original_filename.rsplit(
                ".",
                1
            )[1].lower()

            unique_filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            file_path = os.path.join(
                upload_folder,
                unique_filename,
            )

            image.save(file_path)

            product_image = ProductImage(
                image_url=(
                    f"/static/uploads/products/"
                    f"{unique_filename}"
                ),
                product_id=product.id,
                is_primary=(
                    image_number == 0
                ),
            )

            db.session.add(product_image)

            image_number += 1

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        db.session.commit()

        flash(
            "Product updated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "admin_products.products"
            )
        )

    return render_template(
        "admin/product_form.html",
        form=form,
        title="Edit Product",
    )


# ============================================================
# DELETE PRODUCT
# ============================================================

@products_bp.route(
    "/<int:product_id>/delete",
    methods=["POST"],
)
def delete_product(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    # --------------------------------------------------------
    # DELETE IMAGE FILES
    # --------------------------------------------------------

    for image in product.images:

        if image.image_url:

            filename = os.path.basename(
                image.image_url
            )

            file_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                filename,
            )

            if os.path.exists(file_path):

                os.remove(file_path)

    # --------------------------------------------------------
    # DELETE PRODUCT
    # --------------------------------------------------------

    db.session.delete(product)

    db.session.commit()

    flash(
        "Product deleted successfully.",
        "success",
    )

    return redirect(
        url_for(
            "admin_products.products"
        )
    )