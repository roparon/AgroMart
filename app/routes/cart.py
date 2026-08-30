from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
)

from flask_login import (
    login_required,
    current_user,
)

from app import db
from app import csrf

from app.models.cart import Cart, CartItem
from app.models.product import Product


cart_bp = Blueprint("cart", __name__)


# ============================================================
# VIEW CART
# ============================================================

@cart_bp.route("/")
@login_required
def cart():

    cart = Cart.query.filter_by(
        user_id=current_user.id
    ).first()

    if not cart:
        cart = Cart(
            user_id=current_user.id
        )

        db.session.add(cart)
        db.session.commit()

    total = sum(
        item.product.price * item.quantity
        for item in cart.items
    )

    return render_template(
        "cart.html",
        cart=cart,
        total=total,
    )


# ============================================================
# ADD PRODUCT TO CART
# ============================================================

@cart_bp.route(
    "/add/<int:product_id>",
    methods=["POST"]
)
@login_required
def add_to_cart(product_id):

    product = Product.query.get_or_404(
        product_id
    )

    if product.stock <= 0:

        flash(
            "This product is currently out of stock.",
            "danger",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    cart = Cart.query.filter_by(
        user_id=current_user.id
    ).first()

    if not cart:

        cart = Cart(
            user_id=current_user.id
        )

        db.session.add(cart)
        db.session.flush()

    cart_item = CartItem.query.filter_by(
        cart_id=cart.id,
        product_id=product.id,
    ).first()

    if cart_item:

        if cart_item.quantity >= product.stock:

            flash(
                "You cannot add more than the available stock.",
                "warning",
            )

            return redirect(
                url_for(
                    "product.product_details",
                    id=product.id,
                )
            )

        cart_item.quantity += 1

    else:

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=1,
        )

        db.session.add(cart_item)

    db.session.commit()

    flash(
        f"{product.name} added to your cart.",
        "success",
    )

    return redirect(
        url_for("cart.cart")
    )


# ============================================================
# UPDATE CART ITEM
# ============================================================

@cart_bp.route(
    "/update/<int:item_id>",
    methods=["POST"]
)
@login_required
def update_cart(item_id):

    cart_item = CartItem.query.get_or_404(
        item_id
    )

    if cart_item.cart.user_id != current_user.id:

        flash(
            "You are not allowed to modify this cart.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    quantity = int(
        request.form.get(
            "quantity",
            1,
        )
    )

    if quantity < 1:

        db.session.delete(cart_item)

    elif quantity > cart_item.product.stock:

        flash(
            "Requested quantity exceeds available stock.",
            "warning",
        )

    else:

        cart_item.quantity = quantity

    db.session.commit()

    return redirect(
        url_for("cart.cart")
    )


# ============================================================
# REMOVE CART ITEM
# ============================================================

@cart_bp.route(
    "/remove/<int:item_id>",
    methods=["POST"]
)
@login_required
def remove_from_cart(item_id):

    cart_item = CartItem.query.get_or_404(
        item_id
    )

    if cart_item.cart.user_id != current_user.id:

        flash(
            "You are not allowed to modify this cart.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )
    product_name = cart_item.product.name
    db.session.delete(cart_item)

    db.session.commit()

    flash(
        f"{product_name} removed from your cart.",
        "success",
    )

    return redirect(
        url_for("cart.cart")
    )


# ============================================================
# CHECKOUT
# ============================================================
@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
@csrf.exempt
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()

    if not cart or not cart.items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart.cart"))

    # IF USER SUBMITS THE FORM (CLICKED PLACE ORDER)
    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        shipping_address = request.form.get("shipping_address")
        payment_method = request.form.get("payment_method")

        # TODO: Save the order to your database here (e.g., Order model)
        # TODO: Clear the cart or perform M-Pesa STK push logic

        flash("Order placed successfully!", "success")
        return redirect(url_for("cart.cart"))  # Redirect to success or cart page

    # IF USER IS JUST VIEWING THE PAGE (GET REQUEST)
    total = sum(item.product.price * item.quantity for item in cart.items)

    return render_template(
        "checkout.html",
        cart=cart,
        total=total,
    )