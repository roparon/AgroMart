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

from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

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

    try:
        items = (
            Wishlist.query
            .filter_by(user_id=current_user.id)
            .order_by(Wishlist.created_at.desc())
            .all()
        )

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST PAGE DATABASE ERROR: {e}")

        flash(
            "Unable to load your wishlist right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for("product.products")
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

    try:
        product = Product.query.get(product_id)

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST ADD PRODUCT LOOKUP ERROR: {e}")

        flash(
            "Unable to find this product right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for("product.products")
        )

    if product is None:

        flash(
            "This product could not be found.",
            "warning"
        )

        return redirect(
            url_for("product.products")
        )

    if not product.is_active:

        flash(
            "This product is no longer available.",
            "warning"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    try:
        existing = Wishlist.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST ADD CHECK ERROR: {e}")

        flash(
            "Unable to check your wishlist right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    if existing:

        flash(
            f"{product.name} is already in your wishlist.",
            "info"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    item = Wishlist(
        user_id=current_user.id,
        product_id=product.id
    )

    db.session.add(item)

    try:

        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        flash(
            "This product is already in your wishlist.",
            "info"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST ADD DATABASE ERROR: {e}")

        flash(
            "Unable to add this product to your wishlist.",
            "danger"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    except Exception as e:

        db.session.rollback()

        print(f"WISHLIST ADD ERROR: {e}")

        flash(
            "Unable to add this product to your wishlist.",
            "danger"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    flash(
        f"{product.name} added to your wishlist.",
        "success"
    )

    return redirect(
        url_for(
            "product.product_details",
            id=product.id
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

    try:
        item = Wishlist.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST REMOVE LOOKUP ERROR: {e}")

        flash(
            "Unable to access your wishlist right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for("wishlist.wishlist")
        )

    if not item:

        flash(
            "Product is not in your wishlist.",
            "info"
        )

        return redirect(
            url_for("wishlist.wishlist")
        )

    try:

        db.session.delete(item)
        db.session.commit()

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST REMOVE DATABASE ERROR: {e}")

        flash(
            "Unable to remove the product from your wishlist.",
            "danger"
        )

        return redirect(
            url_for("wishlist.wishlist")
        )

    except Exception as e:

        db.session.rollback()

        print(f"WISHLIST REMOVE ERROR: {e}")

        flash(
            "Unable to remove the product from your wishlist.",
            "danger"
        )

        return redirect(
            url_for("wishlist.wishlist")
        )

    flash(
        "Product removed from your wishlist.",
        "success"
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

    try:
        product = Product.query.get(product_id)

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST TOGGLE PRODUCT LOOKUP ERROR: {e}")

        flash(
            "Unable to find this product right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for("product.products")
        )

    if product is None:

        flash(
            "This product could not be found.",
            "warning"
        )

        return redirect(
            url_for("product.products")
        )

    if not product.is_active:

        flash(
            "This product is no longer available.",
            "warning"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    try:
        item = Wishlist.query.filter_by(
            user_id=current_user.id,
            product_id=product.id
        ).first()

    except SQLAlchemyError as e:

        db.session.rollback()

        print(f"WISHLIST TOGGLE CHECK ERROR: {e}")

        flash(
            "Unable to check your wishlist right now. Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id
            )
        )

    if item:

        try:

            db.session.delete(item)
            db.session.commit()

        except SQLAlchemyError as e:

            db.session.rollback()

            print(f"WISHLIST TOGGLE REMOVE DATABASE ERROR: {e}")

            flash(
                "Unable to remove this product from your wishlist.",
                "danger"
            )

            return redirect(
                url_for(
                    "product.product_details",
                    id=product.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(f"WISHLIST TOGGLE REMOVE ERROR: {e}")

            flash(
                "Unable to remove this product from your wishlist.",
                "danger"
            )

            return redirect(
                url_for(
                    "product.product_details",
                    id=product.id
                )
            )

        flash(
            f"{product.name} removed from your wishlist.",
            "success"
        )

    else:

        new_item = Wishlist(
            user_id=current_user.id,
            product_id=product.id
        )

        db.session.add(new_item)

        try:

            db.session.commit()

        except IntegrityError:

            db.session.rollback()

            flash(
                "This product is already in your wishlist.",
                "info"
            )

        except SQLAlchemyError as e:

            db.session.rollback()

            print(f"WISHLIST TOGGLE ADD DATABASE ERROR: {e}")

            flash(
                "Unable to add this product to your wishlist.",
                "danger"
            )

        except Exception as e:

            db.session.rollback()

            print(f"WISHLIST TOGGLE ADD ERROR: {e}")

            flash(
                "Unable to add this product to your wishlist.",
                "danger"
            )

        else:

            flash(
                f"{product.name} added to your wishlist.",
                "success"
            )

    return redirect(
        url_for(
            "product.product_details",
            id=product.id
        )
    )