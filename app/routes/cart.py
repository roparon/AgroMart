from decimal import Decimal
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
)

from flask_login import (
    login_required,
    current_user,
)

from app import db
from app.services.email_service import send_email
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.order import Order, OrderItem


cart_bp = Blueprint("cart", __name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_or_create_cart():
    """
    Get the logged-in user's cart.

    If the user does not have a cart yet, create one.
    """
    cart = Cart.query.filter_by(
        user_id=current_user.id
    ).first()

    if not cart:
        cart = Cart(
            user_id=current_user.id
        )

        db.session.add(cart)
        db.session.flush()

    return cart


def get_discounted_price(product):
    """
    Calculate the final selling price of a product.

    This calculation is always performed on the server.
    """

    price = Decimal(str(product.price))
    discount = Decimal(str(product.discount or 0))

    # Protect against invalid discount values.
    if discount < 0:
        discount = Decimal("0")

    if discount > 100:
        discount = Decimal("100")

    discounted_price = price - (
        price * discount / Decimal("100")
    )

    return discounted_price.quantize(
        Decimal("0.01")
    )


def calculate_cart_total(cart):
    """
    Calculate the cart total using the current
    server-side discounted prices.
    """

    total = Decimal("0.00")

    for item in cart.items:
        if not item.product:
            continue

        total += (
            get_discounted_price(item.product)
            * item.quantity
        )

    return total.quantize(
        Decimal("0.01")
    )


def safe_quantity(value, default=1):
    """
    Safely convert a submitted quantity into an integer.
    """

    try:
        quantity = int(value)

        if quantity < 1:
            return default

        return quantity

    except (TypeError, ValueError):
        return default


# ============================================================
# VIEW CART
# ============================================================

@cart_bp.route("/")
@login_required
def cart():

    cart = get_or_create_cart()

    # Remove products that no longer exist.
    removed_items = False

    for item in list(cart.items):

        if not item.product:
            db.session.delete(item)
            removed_items = True

    if removed_items:
        db.session.commit()

    total = calculate_cart_total(cart)

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

    # --------------------------------------------------------
    # PRODUCT AVAILABILITY
    # --------------------------------------------------------

    if not product.is_active:

        flash(
            "This product is no longer available.",
            "danger",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
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

    # --------------------------------------------------------
    # REQUESTED QUANTITY
    # --------------------------------------------------------

    requested_quantity = safe_quantity(
        request.form.get("quantity", 1)
    )

    if requested_quantity > product.stock:

        flash(
            f"Only {product.stock} unit(s) "
            f"of {product.name} are available.",
            "warning",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    # --------------------------------------------------------
    # GET / CREATE CART
    # --------------------------------------------------------

    cart = get_or_create_cart()

    # --------------------------------------------------------
    # FIND EXISTING ITEM
    # --------------------------------------------------------

    cart_item = CartItem.query.filter_by(
        cart_id=cart.id,
        product_id=product.id,
    ).first()

    if cart_item:

        new_quantity = (
            cart_item.quantity
            + requested_quantity
        )

        if new_quantity > product.stock:

            flash(
                f"You can only have up to "
                f"{product.stock} unit(s) "
                f"of {product.name} in your cart.",
                "warning",
            )

            return redirect(
                url_for(
                    "product.product_details",
                    id=product.id,
                )
            )

        cart_item.quantity = new_quantity

    else:

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=requested_quantity,
        )

        db.session.add(cart_item)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to add this product to your cart. "
            "Please try again.",
            "danger",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    flash(
        f"{requested_quantity} x {product.name} added to your cart.",
        "success",
    )

    return redirect(
        url_for("cart.cart")
    )


# ============================================================
# BUY NOW
# ============================================================

@cart_bp.route(
    "/buy-now/<int:product_id>",
    methods=["POST"]
)
@login_required
def buy_now(product_id):

    product = Product.query.get_or_404(product_id)

    # --------------------------------------------------------
    # PRODUCT AVAILABILITY
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
    # STOCK CHECK
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GET REQUESTED QUANTITY
    # --------------------------------------------------------

    try:
        quantity = int(
            request.form.get(
                "quantity",
                1,
            )
        )
    except (TypeError, ValueError):
        quantity = 1

    # --------------------------------------------------------
    # QUANTITY VALIDATION
    # --------------------------------------------------------

    if quantity < 1:
        quantity = 1

    if quantity > product.stock:
        flash(
            f"Only {product.stock} unit(s) of "
            f"{product.name} are available.",
            "warning",
        )

        return redirect(
            url_for(
                "product.product_details",
                id=product.id,
            )
        )

    # --------------------------------------------------------
    # STORE TEMPORARY BUY-NOW ORDER
    # --------------------------------------------------------

    session["buy_now"] = {
        "product_id": product.id,
        "quantity": quantity,
    }

    session.modified = True

    # --------------------------------------------------------
    # GO DIRECTLY TO CHECKOUT
    # --------------------------------------------------------

    return redirect(
        url_for("cart.checkout")
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

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    if not cart_item.cart:
        flash(
            "Cart item not found.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    if cart_item.cart.user_id != current_user.id:

        flash(
            "You are not allowed to modify this cart.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    product = cart_item.product

    # --------------------------------------------------------
    # PRODUCT CHECK
    # --------------------------------------------------------

    if not product or not product.is_active:

        db.session.delete(cart_item)
        db.session.commit()

        flash(
            "This product is no longer available "
            "and was removed from your cart.",
            "warning",
        )

        return redirect(
            url_for("cart.cart")
        )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    quantity = safe_quantity(
        request.form.get("quantity"),
        default=1,
    )

    # --------------------------------------------------------
    # REMOVE WHEN ZERO / INVALID
    # --------------------------------------------------------

    raw_quantity = request.form.get(
        "quantity",
        ""
    ).strip()

    try:
        requested_quantity = int(raw_quantity)
    except (TypeError, ValueError):
        requested_quantity = 1

    if requested_quantity <= 0:

        db.session.delete(cart_item)

        db.session.commit()

        flash(
            f"{product.name} removed from your cart.",
            "success",
        )

        return redirect(
            url_for("cart.cart")
        )

    # --------------------------------------------------------
    # STOCK VALIDATION
    # --------------------------------------------------------

    if quantity > product.stock:

        flash(
            f"Only {product.stock} unit(s) "
            f"of {product.name} are available.",
            "warning",
        )

        return redirect(
            url_for("cart.cart")
        )

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    cart_item.quantity = quantity

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to update your cart.",
            "danger",
        )

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

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    if not cart_item.cart:

        flash(
            "Cart item not found.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    if cart_item.cart.user_id != current_user.id:

        flash(
            "You are not allowed to modify this cart.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    product_name = (
        cart_item.product.name
        if cart_item.product
        else "Product"
    )

    db.session.delete(cart_item)

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to remove the item.",
            "danger",
        )

        return redirect(
            url_for("cart.cart")
        )

    flash(
        f"{product_name} removed from your cart.",
        "success",
    )

    return redirect(
        url_for("cart.cart")
    )


# ============================================================
# CHECKOUT
#=========================================================

@cart_bp.route(
    "/checkout",
    methods=["GET", "POST"]
)
@login_required
def checkout():

    from decimal import Decimal
    import uuid

    # ========================================================
    # DETERMINE CHECKOUT MODE
    # ========================================================

    buy_now_data = session.get("buy_now")

    buy_now_mode = bool(buy_now_data)

    # ========================================================
    # BUY NOW CHECKOUT
    # ========================================================

    if buy_now_mode:

        product_id = buy_now_data.get("product_id")
        quantity = buy_now_data.get("quantity", 1)

        # ----------------------------------------------------
        # VALIDATE SESSION DATA
        # ----------------------------------------------------

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):

            session.pop("buy_now", None)

            flash(
                "Your Buy Now session has expired. "
                "Please try again.",
                "warning",
            )

            return redirect(
                url_for("product.products")
            )

        if quantity < 1:
            session.pop("buy_now", None)

            flash(
                "Invalid purchase quantity.",
                "danger",
            )

            return redirect(
                url_for("product.products")
            )

        # ----------------------------------------------------
        # GET PRODUCT
        # ----------------------------------------------------

        product = Product.query.get(product_id)

        if not product or not product.is_active:

            session.pop("buy_now", None)

            flash(
                "This product is no longer available.",
                "danger",
            )

            return redirect(
                url_for("product.products")
            )

        # ----------------------------------------------------
        # STOCK VALIDATION
        # ----------------------------------------------------

        if product.stock < quantity:

            session.pop("buy_now", None)

            flash(
                f"Only {product.stock} unit(s) of "
                f"{product.name} are currently available.",
                "warning",
            )

            return redirect(
                url_for(
                    "product.product_details",
                    id=product.id,
                )
            )

        # ----------------------------------------------------
        # DISCOUNTED PRICE
        # ----------------------------------------------------

        price = Decimal(str(product.price))

        discount = Decimal(
            str(product.discount or 0)
        )

        if discount < 0:
            discount = Decimal("0")

        if discount > 100:
            discount = Decimal("100")

        unit_price = (
            price
            - (
                price
                * discount
                / Decimal("100")
            )
        ).quantize(
            Decimal("0.01")
        )

        total = (
            unit_price
            * Decimal(quantity)
        ).quantize(
            Decimal("0.01")
        )

        # ----------------------------------------------------
        # CREATE BUY-NOW ITEMS FOR TEMPLATE
        # ----------------------------------------------------

        checkout_items = [
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": total,
            }
        ]

    # ========================================================
    # NORMAL CART CHECKOUT
    # ========================================================

    else:

        cart = Cart.query.filter_by(
            user_id=current_user.id
        ).first()

        if not cart or not cart.items:

            flash(
                "Your cart is empty.",
                "warning",
            )

            return redirect(
                url_for("cart.cart")
            )

        checkout_items = []

        total = Decimal("0")

        # ----------------------------------------------------
        # VALIDATE CART
        # ----------------------------------------------------

        for cart_item in cart.items:

            product = cart_item.product

            if not product or not product.is_active:

                flash(
                    "One of the products in your cart "
                    "is no longer available.",
                    "danger",
                )

                return redirect(
                    url_for("cart.cart")
                )

            if cart_item.quantity < 1:

                flash(
                    "Invalid quantity detected in your cart.",
                    "danger",
                )

                return redirect(
                    url_for("cart.cart")
                )

            if cart_item.quantity > product.stock:

                flash(
                    f"Only {product.stock} unit(s) of "
                    f"{product.name} are available.",
                    "warning",
                )

                return redirect(
                    url_for("cart.cart")
                )

            # ------------------------------------------------
            # CALCULATE DISCOUNTED PRICE
            # ------------------------------------------------

            price = Decimal(
                str(product.price)
            )

            discount = Decimal(
                str(product.discount or 0)
            )

            if discount < 0:
                discount = Decimal("0")

            if discount > 100:
                discount = Decimal("100")

            unit_price = (
                price
                - (
                    price
                    * discount
                    / Decimal("100")
                )
            ).quantize(
                Decimal("0.01")
            )

            subtotal = (
                unit_price
                * Decimal(cart_item.quantity)
            ).quantize(
                Decimal("0.01")
            )

            checkout_items.append(
                {
                    "cart_item": cart_item,
                    "product": product,
                    "quantity": cart_item.quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

            total += subtotal

        total = total.quantize(
            Decimal("0.01")
        )

    # ========================================================
    # PLACE ORDER
    # ========================================================

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            "",
        ).strip()

        phone = request.form.get(
            "phone",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip()

        shipping_address = request.form.get(
            "shipping_address",
            "",
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            "",
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
        # FINAL STOCK CHECK
        # ----------------------------------------------------
        # This happens again immediately before creating
        # the order so we don't trust an old checkout page.

        for item in checkout_items:

            product = item["product"]
            quantity = item["quantity"]

            if not product.is_active:

                flash(
                    f"{product.name} is no longer available.",
                    "danger",
                )

                return redirect(
                    url_for("cart.checkout")
                )

            if product.stock < quantity:

                flash(
                    f"Only {product.stock} unit(s) of "
                    f"{product.name} remain.",
                    "warning",
                )

                return redirect(
                    url_for("cart.checkout")
                )

        # ----------------------------------------------------
        # GENERATE UNIQUE ORDER CODE
        # ----------------------------------------------------

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
            total_amount=float(total),
            status="Pending",
            shipping_address=shipping_address,
            payment_method=payment_method,
        )

        db.session.add(order)

        # Need order ID before OrderItems
        db.session.flush()

        # ====================================================
        # CREATE ORDER ITEMS
        # ====================================================

        for item in checkout_items:

            product = item["product"]
            quantity = item["quantity"]
            unit_price = item["unit_price"]

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=float(unit_price),
            )

            db.session.add(order_item)

            # ------------------------------------------------
            # REDUCE STOCK
            # ------------------------------------------------

            product.stock -= quantity

        # ====================================================
        # CLEAR ONLY THE CORRECT PURCHASE SOURCE
        # ====================================================

        if buy_now_mode:

            # IMPORTANT:
            # Do NOT touch the user's normal cart.

            session.pop(
                "buy_now",
                None,
            )

        else:

            # Normal checkout:
            # clear the cart as before.

            for item in checkout_items:

                cart_item = item.get(
                    "cart_item"
                )

                if cart_item:

                    db.session.delete(
                        cart_item
                    )

        # ====================================================
        # SAVE TRANSACTION
        # ====================================================

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            # Restore Buy Now session if transaction failed
            if buy_now_mode:

                session["buy_now"] = {
                    "product_id": product_id,
                    "quantity": quantity,
                }

            flash(
                "Something went wrong while placing "
                "your order. Please try again.",
                "danger",
            )

            return redirect(
                url_for("cart.checkout")
            )

        send_email(
            subject=f"Bomet Machineries Ltd Order Confirmation - {order.order_code}",
            recipients=[email],
            template="emails/order_confirmation.html",
            order=order,
        )

        # ====================================================
        # ORDER SUCCESS
        # ====================================================

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

    # ========================================================
    # SHOW CHECKOUT
    # ========================================================

    return render_template(
        "checkout.html",
        cart=(
            None
            if buy_now_mode
            else cart
        ),
        checkout_items=checkout_items,
        total=total,
        buy_now_mode=buy_now_mode,
    )

# ============================================================
# ORDER CONFIRMATION
# ============================================================

@cart_bp.route(
    "/order/<int:order_id>/confirmation"
)
@login_required
def order_confirmation(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    # --------------------------------------------------------
    # SECURITY
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

    orders = (
        Order.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return render_template(
        "my_orders.html",
        orders=orders,
    )


# ============================================================
# ORDER DETAILS
# ============================================================

@cart_bp.route(
    "/orders/<int:order_id>"
)
@login_required
def order_details(order_id):

    order = Order.query.get_or_404(
        order_id
    )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

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