from decimal import Decimal

from flask import (
    Blueprint,
    render_template,
    request,
    session,
)

from flask_login import (
    current_user,
)

from sqlalchemy import or_

from app.models.product import Product
from app.models.category import Category
from app.models.wishlist import Wishlist


product_bp = Blueprint("product", __name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_discounted_price(product):
    """
    Calculate the final selling price on the server.
    """

    price = Decimal(str(product.price))
    discount = Decimal(str(product.discount or 0))

    # Never allow an invalid discount.
    if discount < 0:
        discount = Decimal("0")

    if discount > 100:
        discount = Decimal("100")

    discounted_price = (
        price
        - (
            price
            * discount
            / Decimal("100")
        )
    )

    return discounted_price.quantize(
        Decimal("0.01")
    )


def get_recently_viewed_ids(product_id):
    """
    Store recently viewed product IDs in the user's session.
    """

    recently_viewed = session.get(
        "recently_viewed",
        []
    )

    # Make sure old/invalid session data
    # does not break the application.
    if not isinstance(recently_viewed, list):
        recently_viewed = []

    # Remove current product if already present.
    recently_viewed = [
        item
        for item in recently_viewed
        if item != product_id
    ]

    # Put current product first.
    recently_viewed.insert(
        0,
        product_id
    )

    # Keep only the latest 8.
    recently_viewed = recently_viewed[:8]

    session["recently_viewed"] = recently_viewed

    session.modified = True

    return recently_viewed


# ============================================================
# PRODUCT LIST
# ============================================================

@product_bp.route("/")
def products():

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    category_id = request.args.get(
        "category",
        "",
        type=str
    ).strip()

    min_price = request.args.get(
        "min_price",
        "",
        type=str
    ).strip()

    max_price = request.args.get(
        "max_price",
        "",
        type=str
    ).strip()

    stock_filter = request.args.get(
        "stock",
        "",
        type=str
    ).strip()

    sort = request.args.get(
        "sort",
        "newest",
        type=str
    ).strip()

    # --------------------------------------------------------
    # BASE QUERY
    # --------------------------------------------------------

    query = Product.query.filter_by(
        is_active=True
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        search_term = f"%{search}%"

        query = query.filter(
            or_(
                Product.name.ilike(
                    search_term
                ),

                Product.brand.ilike(
                    search_term
                ),

                Product.sku.ilike(
                    search_term
                ),

                Product.description.ilike(
                    search_term
                ),
            )
        )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    if category_id:

        try:

            category_id_int = int(
                category_id
            )

            query = query.filter(
                Product.category_id
                == category_id_int
            )

        except ValueError:

            category_id = ""

    # --------------------------------------------------------
    # MINIMUM PRICE
    # --------------------------------------------------------

    if min_price:

        try:

            min_price_value = float(
                min_price
            )

            if min_price_value >= 0:

                query = query.filter(
                    Product.price
                    >= min_price_value
                )

            else:

                min_price = ""

        except ValueError:

            min_price = ""

    # --------------------------------------------------------
    # MAXIMUM PRICE
    # --------------------------------------------------------

    if max_price:

        try:

            max_price_value = float(
                max_price
            )

            if max_price_value >= 0:

                query = query.filter(
                    Product.price
                    <= max_price_value
                )

            else:

                max_price = ""

        except ValueError:

            max_price = ""

    # --------------------------------------------------------
    # STOCK FILTER
    # --------------------------------------------------------

    if stock_filter == "in_stock":

        query = query.filter(
            Product.stock > 0
        )

    elif stock_filter == "out_of_stock":

        query = query.filter(
            Product.stock <= 0
        )

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    if sort == "price_low":

        query = query.order_by(
            Product.price.asc()
        )

    elif sort == "price_high":

        query = query.order_by(
            Product.price.desc()
        )

    elif sort == "name_az":

        query = query.order_by(
            Product.name.asc()
        )

    elif sort == "name_za":

        query = query.order_by(
            Product.name.desc()
        )

    elif sort == "oldest":

        query = query.order_by(
            Product.created_at.asc()
        )

    elif sort == "featured":

        query = query.order_by(
            Product.featured.desc(),
            Product.created_at.desc()
        )

    else:

        sort = "newest"

        query = query.order_by(
            Product.created_at.desc()
        )

    # --------------------------------------------------------
    # GET PRODUCTS
    # --------------------------------------------------------

    # products = query.all()
    page = request.args.get("page", 1, type=int)
    per_page = 12

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    products = pagination.items

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = (
        Category.query
        .filter_by(is_active=True)
        .order_by(
            Category.name.asc()
        )
        .all()
    )

    # --------------------------------------------------------
    # PRODUCT DATA
    #
    # Provide calculated prices to the template.
    # --------------------------------------------------------

    product_prices = {}

    for product in products:

        product_prices[
            product.id
        ] = get_discounted_price(
            product
        )

    return render_template(
        "product.html",
        products=products,
        pagination=pagination,
        categories=categories,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        stock_filter=stock_filter,
        sort=sort,
        product_prices=product_prices,
        product_count=pagination.total,
    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

@product_bp.route("/<int:id>")
def product_details(id):

    # --------------------------------------------------------
    # GET PRODUCT
    # --------------------------------------------------------

    product = Product.query.get_or_404(
        id
    )

    # --------------------------------------------------------
    # DO NOT SHOW INACTIVE PRODUCTS
    #
    # Admin can deactivate a product.
    # Customers should not be able to access it publicly.
    # --------------------------------------------------------

    if not product.is_active:

        from flask import abort

        abort(404)

    # --------------------------------------------------------
    # DISCOUNTED PRICE
    # --------------------------------------------------------

    discounted_price = (
        get_discounted_price(product)
    )

    # --------------------------------------------------------
    # STOCK STATUS
    # --------------------------------------------------------

    if product.stock <= 0:

        stock_status = "out_of_stock"

    elif product.stock <= 5:

        stock_status = "low_stock"

    else:

        stock_status = "in_stock"

    # --------------------------------------------------------
    # WISHLIST STATUS
    # --------------------------------------------------------

    is_in_wishlist = False

    if current_user.is_authenticated:

        is_in_wishlist = (
            Wishlist.query
            .filter_by(
                user_id=current_user.id,
                product_id=product.id,
            )
            .first()
            is not None
        )

    # --------------------------------------------------------
    # RELATED PRODUCTS
    #
    # Prefer products from the same category.
    # --------------------------------------------------------

    related_products = (
        Product.query
        .filter(
            Product.is_active.is_(True),
            Product.id != product.id,
            Product.category_id
            == product.category_id,
        )
        .order_by(
            Product.featured.desc(),
            Product.created_at.desc(),
        )
        .limit(8)
        .all()
    )

    # --------------------------------------------------------
    # FALLBACK RELATED PRODUCTS
    #
    # If the category has fewer than 4 products,
    # fill the remaining slots with other products.
    # --------------------------------------------------------

    if len(related_products) < 4:

        existing_ids = [
            item.id
            for item in related_products
        ]

        existing_ids.append(
            product.id
        )

        remaining_products = (
            Product.query
            .filter(
                Product.is_active.is_(True),
                ~Product.id.in_(
                    existing_ids
                ),
            )
            .order_by(
                Product.featured.desc(),
                Product.created_at.desc(),
            )
            .limit(
                8 - len(related_products)
            )
            .all()
        )

        related_products.extend(
            remaining_products
        )

    # --------------------------------------------------------
    # RECENTLY VIEWED
    # --------------------------------------------------------

    recently_viewed_ids = (
        get_recently_viewed_ids(
            product.id
        )
    )

    # Do not show the current product
    # inside the recently viewed products.
    recent_ids_without_current = [
        item
        for item in recently_viewed_ids
        if item != product.id
    ]

    recently_viewed = []

    if recent_ids_without_current:

        recent_products = (
            Product.query
            .filter(
                Product.is_active.is_(True),
                Product.id.in_(
                    recent_ids_without_current
                ),
            )
            .all()
        )

        recent_lookup = {
            item.id: item
            for item in recent_products
        }

        # Preserve session order.
        for product_id in (
            recent_ids_without_current
        ):

            recent_product = (
                recent_lookup.get(
                    product_id
                )
            )

            if recent_product:

                recently_viewed.append(
                    recent_product
                )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = product.category

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "product_details.html",

        product=product,

        category=category,

        discounted_price=discounted_price,

        stock_status=stock_status,

        is_in_wishlist=is_in_wishlist,

        related_products=related_products,

        recently_viewed=recently_viewed,
    )