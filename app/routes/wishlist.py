from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
)

from flask_login import (
    login_required,
    current_user,
)

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.wishlist import Wishlist
from app.models.product import Product


wishlist_bp = Blueprint(
    "wishlist",
    __name__,
)


# ============================================================
# WISHLIST PAGE
# ============================================================

@wishlist_bp.route("/")
@login_required
def wishlist():
    items = (
        Wishlist.query
        .filter_by(user_id=current_user.id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )

    products = [
        item.product
        for item in items
        if item.product and item.product.is_active
    ]

    return render_template(
        "wishlist.html",
        products=products,
        items=items,
    )


# ============================================================
# ADD TO WISHLIST
# ============================================================

@wishlist_bp.route(
    "/add/<int:product_id>",
    methods=["POST"]
)
@login_required
def add_to_wishlist(product_id):

    product = Product.query.get_or_404(product_id)

    # --------------------------------------------------------
    # PRODUCT SECURITY
    # --------------------------------------------------------

    if not product.is_active:
        flash(
            "This product is no longer available.",
            "warning",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    # --------------------------------------------------------
    # CHECK EXISTING WISHLIST ITEM
    # --------------------------------------------------------

    existing = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product.id,
    ).first()

    if existing:
        flash(
            f"{product.name} is already in your wishlist.",
            "info",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    # --------------------------------------------------------
    # CREATE WISHLIST ITEM
    # --------------------------------------------------------

    item = Wishlist(
        user_id=current_user.id,
        product_id=product.id,
    )

    db.session.add(item)

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        flash(
            "This product is already in your wishlist.",
            "info",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    flash(
        f"{product.name} added to your wishlist.",
        "success",
    )

    return redirect(
        url_for(
            "product.product_details",
            id=product.id,
        )
    )


# ============================================================
# REMOVE FROM WISHLIST
# ============================================================

@wishlist_bp.route(
    "/remove/<int:product_id>",
    methods=["POST"]
)
@login_required
def remove_from_wishlist(product_id):

    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product_id,
    ).first()

    if not item:
        flash(
            "Product is not in your wishlist.",
            "info",
        )

        return redirect(
            url_for("wishlist.wishlist")
        )

    db.session.delete(item)
    db.session.commit()

    flash(
        "Product removed from your wishlist.",
        "success",
    )

    return redirect(
        url_for("wishlist.wishlist")
    )


# ============================================================
# TOGGLE WISHLIST
# ============================================================

@wishlist_bp.route(
    "/toggle/<int:product_id>",
    methods=["POST"]
)
@login_required
def toggle_wishlist(product_id):

    product = Product.query.get_or_404(product_id)

    if not product.is_active:
        flash(
            "This product is no longer available.",
            "warning",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product.id,
    ).first()

    if item:
        db.session.delete(item)
        db.session.commit()

        flash(
            f"{product.name} removed from your wishlist.",
            "success",
        )

    else:
        item = Wishlist(
            user_id=current_user.id,
            product_id=product.id,
        )

        db.session.add(item)

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

        else:
            flash(
                f"{product.name} added to your wishlist.",
                "success",
            )

    return redirect(
        url_for(
            "product.product_details",
            id=product.id,
        )
    )