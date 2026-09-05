from decimal import Decimal

from flask import (
    Blueprint,
    render_template,
    request,
    session,
)

from flask_login import current_user

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.models.product import Product
from app.models.category import Category
from app.models.wishlist import Wishlist


product_bp = Blueprint("product", __name__)


# ============================================================
# CONFIGURATION
# ============================================================

PRODUCTS_PER_PAGE = 12
RELATED_PRODUCTS_LIMIT = 8
RECENTLY_VIEWED_LIMIT = 8


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_discounted_price(product):
    """
    Calculate the final selling price safely on the server.
    """

    price = Decimal(str(product.price or 0))
    discount = Decimal(str(product.discount or 0))

    if price < 0:
        price = Decimal("0")

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


def get_stock_status(product):
    """
    Return a consistent stock status for templates.
    """

    if product.stock <= 0:
        return "out_of_stock"

    if product.stock <= 5:
        return "low_stock"

    return "in_stock"


def get_recently_viewed_ids(product_id):
    """
    Store recently viewed product IDs in the user's session.
    """

    recently_viewed = session.get(
        "recently_viewed",
        [],
    )

    if not isinstance(recently_viewed, list):
        recently_viewed = []

    # Remove duplicate/current occurrence.
    recently_viewed = [
        item
        for item in recently_viewed
        if item != product_id
    ]

    # Current product goes first.
    recently_viewed.insert(
        0,
        product_id,
    )

    recently_viewed = recently_viewed[
        :RECENTLY_VIEWED_LIMIT
    ]

    session["recently_viewed"] = recently_viewed
    session.modified = True

    return recently_viewed


def get_active_categories():
    """
    Load active categories once for product listing pages.
    """

    return (
        Category.query
        .filter(
            Category.is_active.is_(True)
        )
        .order_by(
            Category.name.asc()
        )
        .all()
    )


def build_product_prices(products):
    """
    Build a dictionary of server-calculated selling prices.
    """

    return {
        product.id: get_discounted_price(product)
        for product in products
    }


# ============================================================
# PRODUCT LISTING
# ============================================================

@product_bp.route("/")
def products():

    search = request.args.get(
        "search",
        "",
        type=str,
    ).strip()

    category_id = request.args.get(
        "category",
        "",
        type=str,
    ).strip()

    min_price = request.args.get(
        "min_price",
        "",
        type=str,
    ).strip()

    max_price = request.args.get(
        "max_price",
        "",
        type=str,
    ).strip()

    stock_filter = request.args.get(
        "stock",
        "",
        type=str,
    ).strip()

    sort = request.args.get(
        "sort",
        "newest",
        type=str,
    ).strip()

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    if page < 1:
        page = 1

    # --------------------------------------------------------
    # BASE QUERY
    # --------------------------------------------------------

    query = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.is_active.is_(True)
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        search_term = f"%{search}%"

        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.description.ilike(search_term),
            )
        )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    selected_category = None

    if category_id:

        try:

            category_id_int = int(category_id)

            selected_category = (
                Category.query
                .filter(
                    Category.id == category_id_int,
                    Category.is_active.is_(True),
                )
                .first()
            )

            if selected_category:

                query = query.filter(
                    Product.category_id
                    == selected_category.id
                )

            else:

                category_id = ""

        except (ValueError, TypeError):

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

        except (ValueError, TypeError):

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

        except (ValueError, TypeError):

            max_price = ""

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    if stock_filter == "in_stock":

        query = query.filter(
            Product.stock > 0
        )

    elif stock_filter == "out_of_stock":

        query = query.filter(
            Product.stock <= 0
        )

    else:

        stock_filter = ""

    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    if sort == "price_low":

        query = query.order_by(
            Product.price.asc(),
            Product.id.desc(),
        )

    elif sort == "price_high":

        query = query.order_by(
            Product.price.desc(),
            Product.id.desc(),
        )

    elif sort == "name_az":

        query = query.order_by(
            Product.name.asc(),
            Product.id.desc(),
        )

    elif sort == "name_za":

        query = query.order_by(
            Product.name.desc(),
            Product.id.desc(),
        )

    elif sort == "oldest":

        query = query.order_by(
            Product.created_at.asc(),
            Product.id.asc(),
        )

    elif sort == "featured":

        query = query.order_by(
            Product.featured.desc(),
            Product.created_at.desc(),
            Product.id.desc(),
        )

    else:

        sort = "newest"

        query = query.order_by(
            Product.created_at.desc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    pagination = query.paginate(
        page=page,
        per_page=PRODUCTS_PER_PAGE,
        error_out=False,
    )

    products_list = pagination.items

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = get_active_categories()

    # --------------------------------------------------------
    # PRICE DATA
    # --------------------------------------------------------

    product_prices = build_product_prices(
        products_list
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "product.html",
        products=products_list,
        pagination=pagination,
        categories=categories,
        category=selected_category,
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
# SEO-FRIENDLY CATEGORY PAGE
# ============================================================

@product_bp.route("/category/<string:slug>")
def category_products(slug):

    category = (
        Category.query
        .filter(
            Category.slug == slug,
            Category.is_active.is_(True),
        )
        .first_or_404()
    )

    page = request.args.get(
        "page",
        1,
        type=int,
    )

    if page < 1:
        page = 1

    # --------------------------------------------------------
    # CATEGORY PRODUCTS
    # --------------------------------------------------------

    query = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.category_id == category.id,
            Product.is_active.is_(True),
        )
        .order_by(
            Product.featured.desc(),
            Product.created_at.desc(),
            Product.id.desc(),
        )
    )

    pagination = query.paginate(
        page=page,
        per_page=PRODUCTS_PER_PAGE,
        error_out=False,
    )

    products_list = pagination.items

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    categories = get_active_categories()

    # --------------------------------------------------------
    # PRICE DATA
    # --------------------------------------------------------

    product_prices = build_product_prices(
        products_list
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "product.html",
        products=products_list,
        pagination=pagination,
        categories=categories,
        category=category,
        search="",
        category_id=str(category.id),
        min_price="",
        max_price="",
        stock_filter="",
        sort="featured",
        product_prices=product_prices,
        product_count=pagination.total,
    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

@product_bp.route("/<int:id>")
def product_details(id):

    # --------------------------------------------------------
    # PRODUCT + CATEGORY + IMAGES
    # --------------------------------------------------------

    product = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.id == id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # HIDE INACTIVE PRODUCTS
    # --------------------------------------------------------

    if not product.is_active:

        from flask import abort

        abort(404)

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    discounted_price = (
        get_discounted_price(product)
    )

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    stock_status = get_stock_status(
        product
    )

    # --------------------------------------------------------
    # WISHLIST
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
    # --------------------------------------------------------

    related_products = []

    if product.category_id:

        related_products = (
            Product.query
            .options(
                joinedload(Product.category),
                selectinload(Product.images),
            )
            .filter(
                Product.is_active.is_(True),
                Product.id != product.id,
                Product.category_id == product.category_id,
            )
            .order_by(
                Product.featured.desc(),
                Product.created_at.desc(),
                Product.id.desc(),
            )
            .limit(RELATED_PRODUCTS_LIMIT)
            .all()
        )

    # --------------------------------------------------------
    # FALLBACK RELATED PRODUCTS
    # --------------------------------------------------------

    if len(related_products) < 4:

        existing_ids = [
            item.id
            for item in related_products
        ]

        existing_ids.append(
            product.id
        )

        remaining_limit = (
            RELATED_PRODUCTS_LIMIT
            - len(related_products)
        )

        if remaining_limit > 0:

            remaining_products = (
                Product.query
                .options(
                    joinedload(Product.category),
                    selectinload(Product.images),
                )
                .filter(
                    Product.is_active.is_(True),
                    ~Product.id.in_(existing_ids),
                )
                .order_by(
                    Product.featured.desc(),
                    Product.created_at.desc(),
                    Product.id.desc(),
                )
                .limit(remaining_limit)
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

    recent_ids_without_current = [
        item
        for item in recently_viewed_ids
        if item != product.id
    ]

    recently_viewed = []

    if recent_ids_without_current:

        recent_products = (
            Product.query
            .options(
                joinedload(Product.category),
                selectinload(Product.images),
            )
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

        for product_id in recent_ids_without_current:

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