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
from app.models.order import Order, OrderItem

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
# ============================================================
# CHECKOUT
# ============================================================

@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
@csrf.exempt
def checkout():

    cart = Cart.query.filter_by(
        user_id=current_user.id
    ).first()

    # --------------------------------------------------------
    # EMPTY CART
    # --------------------------------------------------------

    if not cart or not cart.items:

        flash(
            "Your cart is empty.",
            "warning",
        )

        return redirect(
            url_for("cart.cart")
        )

    # --------------------------------------------------------
    # CALCULATE TOTAL
    # --------------------------------------------------------

    total = sum(
        item.product.price * item.quantity
        for item in cart.items
    )

    # --------------------------------------------------------
    # PLACE ORDER
    # --------------------------------------------------------

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        shipping_address = request.form.get(
            "shipping_address",
            ""
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            ""
        ).strip()

        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if not full_name:
            flash(
                "Please enter your full name.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        if not phone:
            flash(
                "Please enter your phone number.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        if not email:
            flash(
                "Please enter your email address.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        if not shipping_address:
            flash(
                "Please enter your delivery address.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        if payment_method not in [
            "mpesa",
            "cod",
        ]:

            flash(
                "Please select a valid payment method.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        # ----------------------------------------------------
        # VERIFY STOCK BEFORE CREATING ORDER
        # ----------------------------------------------------

        for cart_item in cart.items:

            product = cart_item.product

            if not product:
                flash(
                    "One of the products in your cart is no longer available.",
                    "danger",
                )

                return redirect(
                    url_for("cart.cart")
                )

            if product.stock < cart_item.quantity:

                flash(
                    f"Only {product.stock} unit(s) of "
                    f"{product.name} are available.",
                    "warning",
                )

                return redirect(
                    url_for("cart.cart")
                )

        # ----------------------------------------------------
        # GENERATE UNIQUE ORDER CODE
        # ----------------------------------------------------

        import uuid

        while True:

            order_code = (
                f"AGM-{uuid.uuid4().hex[:10].upper()}"
            )

            existing_order = Order.query.filter_by(
                order_code=order_code
            ).first()

            if not existing_order:
                break

        # ----------------------------------------------------
        # CREATE ORDER
        # ----------------------------------------------------

        order = Order(
            user_id=current_user.id,
            order_code=order_code,
            total_amount=total,
            status="Pending",
            shipping_address=shipping_address,
            payment_method=payment_method,
        )

        db.session.add(order)

        # We need the order ID before creating OrderItems
        db.session.flush()

        # ----------------------------------------------------
        # CREATE ORDER ITEMS
        # ----------------------------------------------------

        for cart_item in cart.items:

            product = cart_item.product

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                price=product.price,
            )

            db.session.add(order_item)

            # ------------------------------------------------
            # REDUCE PRODUCT STOCK
            # ------------------------------------------------

            product.stock -= cart_item.quantity

        # ----------------------------------------------------
        # CLEAR CART
        # ----------------------------------------------------

        for cart_item in list(cart.items):

            db.session.delete(cart_item)

        # ----------------------------------------------------
        # SAVE EVERYTHING
        # ----------------------------------------------------

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "Something went wrong while placing your order. "
                "Please try again.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        # ----------------------------------------------------
        # ORDER SUCCESS
        # ----------------------------------------------------

        flash(
            f"Order {order.order_code} placed successfully!",
            "success",
        )

        return redirect(
            url_for(
                "cart.order_confirmation",
                order_id=order.id,
            )
        )

    # --------------------------------------------------------
    # SHOW CHECKOUT PAGE
    # --------------------------------------------------------

    return render_template(
        "checkout.html",
        cart=cart,
        total=total,
    )

# ============================================================
# ORDER CONFIRMATION
# ============================================================

# ============================================================
# ORDER CONFIRMATION
# ============================================================

@cart_bp.route("/order/<int:order_id>/confirmation")
@login_required
def order_confirmation(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    # --------------------------------------------------------
    # SECURITY
    # Make sure the order belongs to the logged-in user
    # --------------------------------------------------------

    if order.user_id != current_user.id:

        flash(
            "You are not authorized to view this order.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    return render_template(
        "order_confirmation.html",
        order=order,
    )

    # ============================================================
# MY ORDERS
# ============================================================

@cart_bp.route("/orders")
@login_required
def my_orders():

    orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "my_orders.html",
        orders=orders,
    )

    # ============================================================
# ORDER DETAILS
# ============================================================

@cart_bp.route("/orders/<int:order_id>")
@login_required
def order_details(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    # SECURITY CHECK

    if order.user_id != current_user.id:

        flash(
            "You are not authorized to view this order.",
            "danger",
        )

        return redirect(
            url_for("cart.my_orders")
        )

    return render_template(
        "order_details.html",
        order=order,
    )