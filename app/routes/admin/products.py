from email.mime import image

from flask import (Blueprint, render_template, redirect, url_for, flash, request, current_app)
from app import db
from app.forms.product_forms import ProductForm
from app.models.product import Product
from app.models.category import Category
import os
import uuid
from werkzeug.utils import secure_filename
from app.models.product_image import ProductImage
from app.routes import product


products_bp = Blueprint("admin_products", __name__)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
def allowed_image(filename):
    return ("." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS)


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

    # --------------------------------------------------------
    # LOAD ACTIVE CATEGORIES
    # --------------------------------------------------------

    categories = Category.query.filter_by(
        is_active=True
    ).order_by(
        Category.name.asc()
    ).all()

    form.category.choices = [
        (category.id, category.name)
        for category in categories
    ]

    # --------------------------------------------------------
    # FORM SUBMISSION
    # --------------------------------------------------------

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

        # Flush gives the product its database ID
        # before the final commit.
        db.session.flush()

        # ----------------------------------------------------
        # IMAGE UPLOAD DIRECTORY
        # ----------------------------------------------------

        upload_folder = current_app.config["UPLOAD_FOLDER"]

        os.makedirs(
            upload_folder,
            exist_ok=True,
        )

        # ----------------------------------------------------
        # GET UPLOADED IMAGES
        # ----------------------------------------------------

        uploaded_images = request.files.getlist("images")

        image_number = 0

        for image in uploaded_images:

            # Ignore empty file inputs
            if not image or not image.filename:
                continue

            # Check extension
            if not allowed_image(image.filename):

                flash(
                    f"Invalid image type: {image.filename}. "
                    "Allowed types are JPG, JPEG, PNG and WEBP.",
                    "danger",
                )

                db.session.rollback()

                return render_template(
                    "admin/product_form.html",
                    form=form,
                    title="Add Product",
                )

            # ------------------------------------------------
            # CREATE SAFE UNIQUE FILENAME
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
            # SAVE IMAGE TO DISK
            # ------------------------------------------------

            image.save(file_path)

            # ------------------------------------------------
            # CREATE DATABASE RECORD
            # ------------------------------------------------

            product_image = ProductImage(
                image_url=(
                    f"/static/uploads/products/"
                    f"{unique_filename}"
                ),
                product_id=product.id,
                is_primary=(image_number == 0),
            )

            db.session.add(product_image)

            image_number += 1

        # ----------------------------------------------------
        # SAVE EVERYTHING
        # ----------------------------------------------------

        db.session.commit()

        flash(
            "Product created successfully.",
            "success",
        )

        return redirect(
            url_for("admin_products.products")
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

    if form.validate_on_submit():

        # Check duplicate SKU
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

        # Check duplicate slug
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

        db.session.commit()

        flash(
            "Product updated successfully.",
            "success",
        )

        return redirect(
            url_for("admin_products.products")
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

    db.session.delete(product)
    db.session.commit()

    flash(
        "Product deleted successfully.",
        "success",
    )
    return redirect(
        url_for("admin_products.products")
    )