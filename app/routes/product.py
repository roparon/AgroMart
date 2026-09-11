from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    render_template,
    request,
    session,
    abort,
)

from flask_login import current_user

from sqlalchemy import or_, and_, func
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

# Maximum number of related search suggestions shown
RELATED_SEARCHES_LIMIT = 8


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_discounted_price(product):
    """
    Calculate the final selling price safely on the server.
    """

    try:
        price = Decimal(str(product.price or 0))
    except (InvalidOperation, ValueError, TypeError):
        price = Decimal("0")

    try:
        discount = Decimal(str(product.discount or 0))
    except (InvalidOperation, ValueError, TypeError):
        discount = Decimal("0")

    # Never allow a negative price.
    if price < 0:
        price = Decimal("0")

    # Keep discount within a safe range.
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

    stock = product.stock or 0

    if stock <= 0:
        return "out_of_stock"

    if stock <= 5:
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
    recently_viewed.insert(0, product_id)

    # Keep only latest products.
    recently_viewed = recently_viewed[
        :RECENTLY_VIEWED_LIMIT
    ]

    session["recently_viewed"] = recently_viewed
    session.modified = True

    return recently_viewed


def get_active_categories():
    """
    Load active categories.
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


def get_wishlist_product_ids():
    """
    Return product IDs already in the
    authenticated user's wishlist.
    """

    if not current_user.is_authenticated:
        return set()

    wishlist_items = (
        Wishlist.query
        .filter_by(
            user_id=current_user.id
        )
        .all()
    )

    return {
        item.product_id
        for item in wishlist_items
    }


def build_product_prices(products):
    """
    Build server-calculated selling prices.
    """

    return {
        product.id: get_discounted_price(product)
        for product in products
    }


def parse_price(value):
    """
    Safely parse a price query parameter.

    Returns:
        Decimal value or None.
    """

    if not value:
        return None

    try:
        number = Decimal(str(value).strip())

        if number < 0:
            return None

        return number

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None


def get_listing_parameters():
    """
    Read and normalize common product-listing parameters.

    Used by both:
        /products
        /products/category/<slug>
    """

    search = request.args.get(
        "search",
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

    # --------------------------------------------------------
    # RANDOM IS NOW THE DEFAULT
    # --------------------------------------------------------

    sort = request.args.get(
        "sort",
        "random",
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
    # PRICE VALIDATION
    # --------------------------------------------------------

    min_price_value = parse_price(min_price)
    max_price_value = parse_price(max_price)

    if min_price and min_price_value is None:
        min_price = ""

    if max_price and max_price_value is None:
        max_price = ""

    # If maximum is lower than minimum,
    # discard the maximum filter rather than creating
    # a confusing empty result.
    if (
        min_price_value is not None
        and max_price_value is not None
        and max_price_value < min_price_value
    ):
        max_price = ""
        max_price_value = None

    # --------------------------------------------------------
    # STOCK VALIDATION
    # --------------------------------------------------------

    if stock_filter not in {
        "in_stock",
        "out_of_stock",
    }:
        stock_filter = ""

    # --------------------------------------------------------
    # SORT VALIDATION
    # --------------------------------------------------------

    allowed_sorts = {
        "random",
        "newest",
        "featured",
        "price_low",
        "price_high",
        "name_az",
        "name_za",
        "oldest",
    }

    if sort not in allowed_sorts:
        sort = "random"

    return {
        "search": search,
        "min_price": min_price,
        "max_price": max_price,
        "min_price_value": min_price_value,
        "max_price_value": max_price_value,
        "stock_filter": stock_filter,
        "sort": sort,
        "page": page,
    }


def apply_listing_filters(
    query,
    search="",
    min_price_value=None,
    max_price_value=None,
    stock_filter="",
):
    """
    Apply common search, price and stock filters.
    """

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
    # MINIMUM PRICE
    # --------------------------------------------------------

    if min_price_value is not None:

        query = query.filter(
            Product.price >= min_price_value
        )

    # --------------------------------------------------------
    # MAXIMUM PRICE
    # --------------------------------------------------------

    if max_price_value is not None:

        query = query.filter(
            Product.price <= max_price_value
        )

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

    return query


def get_random_order_expression(query):
    """
    Return the correct random-order SQL expression
    for the active database.

    MySQL / MariaDB:
        RAND()

    SQLite / PostgreSQL and most other databases:
        RANDOM()
    """

    try:
        bind = query.session.get_bind()

        if bind is not None:

            dialect_name = (
                bind.dialect.name.lower()
            )

            if dialect_name in {
                "mysql",
                "mariadb",
            }:
                return func.rand()

    except Exception:
        # If the database dialect cannot be determined,
        # fall back to SQLAlchemy's standard RANDOM().
        pass

    return func.random()


def apply_sorting(query, sort):
    """
    Apply product sorting.

    RANDOM is the default storefront behavior.

    This means customers do not continually see the same
    product in the same position when they revisit or
    refresh the product listing.

    Explicit sorting options remain available.
    """

    # --------------------------------------------------------
    # RANDOM
    # --------------------------------------------------------

    if sort == "random":

        return query.order_by(
            get_random_order_expression(query)
        )

    # --------------------------------------------------------
    # PRICE: LOW TO HIGH
    # --------------------------------------------------------

    if sort == "price_low":

        return query.order_by(
            Product.price.asc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # PRICE: HIGH TO LOW
    # --------------------------------------------------------

    if sort == "price_high":

        return query.order_by(
            Product.price.desc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # NAME A-Z
    # --------------------------------------------------------

    if sort == "name_az":

        return query.order_by(
            Product.name.asc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # NAME Z-A
    # --------------------------------------------------------

    if sort == "name_za":

        return query.order_by(
            Product.name.desc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # OLDEST
    # --------------------------------------------------------

    if sort == "oldest":

        return query.order_by(
            Product.created_at.asc(),
            Product.id.asc(),
        )

    # --------------------------------------------------------
    # FEATURED
    # --------------------------------------------------------

    if sort == "featured":

        return query.order_by(
            Product.featured.desc(),
            Product.created_at.desc(),
            Product.id.desc(),
        )

    # --------------------------------------------------------
    # DEFAULT = RANDOM
    # --------------------------------------------------------

    return query.order_by(
        get_random_order_expression(query)
    )


def build_product_query():
    """
    Base active-product query with eager loading.
    """

    return (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.is_active.is_(True)
        )
    )


# ============================================================
# RELATED PRODUCT HELPERS
# ============================================================

def normalize_search_words(text):
    """
    Convert a product name into useful search terms.

    Very short/common words are ignored so that a product such
    as '20HP Diesel Posho Mill' does not create useless searches
    such as '20HP' or 'diesel' alone.
    """

    if not text:
        return []

    separators = [
        "-",
        "_",
        "/",
        ",",
        ".",
        "(",
        ")",
        "[",
        "]",
    ]

    cleaned = str(text).lower()

    for separator in separators:
        cleaned = cleaned.replace(
            separator,
            " ",
        )

    words = cleaned.split()

    ignored_words = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "model",
        "new",
        "used",
        "type",
        "machine",
        "machinery",
        "equipment",
    }

    result = []

    for word in words:

        word = word.strip()

        if not word:
            continue

        if word in ignored_words:
            continue

        if len(word) < 3:
            continue

        if word not in result:
            result.append(word)

    return result


def build_related_searches(product):
    """
    Build useful search suggestions for the current product.

    Example:

        Product:
            Diesel Posho Mill 20HP

        Suggestions:
            Posho Mills
            Diesel Posho Mill
            Posho Mill
            20HP Posho Mill
            Posho Mill Spare Parts
            Posho Mill Accessories
    """

    searches = []

    def add_search(label, query=None):

        if not label:
            return

        label = str(label).strip()

        if not label:
            return

        normalized = label.lower()

        for existing in searches:

            if existing["label"].lower() == normalized:
                return

        if query is None:
            query = label

        searches.append({
            "label": label,
            "query": query,
        })


    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    if product.category:

        category_name = (
            product.category.name or ""
        ).strip()

        if category_name:

            add_search(
                category_name,
                category_name,
            )


    # --------------------------------------------------------
    # PRODUCT NAME
    # --------------------------------------------------------

    product_name = (
        product.name or ""
    ).strip()

    words = normalize_search_words(
        product_name
    )


    # Full product name
    if product_name:

        add_search(
            product_name,
            product_name,
        )


    # --------------------------------------------------------
    # PRODUCT TYPE / CORE TERMS
    # --------------------------------------------------------

    if len(words) >= 2:

        # First two meaningful words
        add_search(
            " ".join(words[:2]).title(),
            " ".join(words[:2]),
        )


    # Three-word combination
    if len(words) >= 3:

        add_search(
            " ".join(words[:3]).title(),
            " ".join(words[:3]),
        )


    # --------------------------------------------------------
    # BRAND
    # --------------------------------------------------------

    brand = (
        getattr(product, "brand", None)
        or ""
    ).strip()

    if brand:

        add_search(
            f"{brand} machinery",
            brand,
        )


    # --------------------------------------------------------
    # SPARE PARTS / ACCESSORIES
    # --------------------------------------------------------

    if words:

        core_term = " ".join(
            words[:2]
        )

        add_search(
            f"{core_term.title()} spare parts",
            f"{core_term} spare parts",
        )

        add_search(
            f"{core_term.title()} accessories",
            f"{core_term} accessories",
        )


    # --------------------------------------------------------
    # PRICE-AGNOSTIC RELATED SEARCH
    # --------------------------------------------------------

    if product.category:

        category_name = (
            product.category.name or ""
        ).strip()

        if category_name:

            add_search(
                f"{category_name} products",
                category_name,
            )


    return searches[
        :RELATED_SEARCHES_LIMIT
    ]


def get_related_products(product):
    """
    Find related products using a relevance-first strategy.

    Priority:

        1. Same category
        2. Matching product-name terms
        3. Matching brand
        4. Featured products
        5. In-stock products
        6. Newer products

    This intentionally avoids random products whenever
    enough relevant products exist.
    """

    # --------------------------------------------------------
    # CURRENT PRODUCT INFORMATION
    # --------------------------------------------------------

    category_id = product.category_id

    product_name = (
        product.name or ""
    ).strip()

    brand = (
        getattr(product, "brand", None)
        or ""
    ).strip()

    search_words = normalize_search_words(
        product_name
    )


    # --------------------------------------------------------
    # BUILD CANDIDATE QUERY
    # --------------------------------------------------------

    query = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.is_active.is_(True),
            Product.id != product.id,
        )
    )


    # --------------------------------------------------------
    # RELEVANCE CONDITIONS
    # --------------------------------------------------------

    relevance_conditions = []


    # Same category
    if category_id:

        relevance_conditions.append(
            Product.category_id == category_id
        )


    # Product-name terms
    for word in search_words[:5]:

        term = f"%{word}%"

        relevance_conditions.append(
            or_(
                Product.name.ilike(term),
                Product.description.ilike(term),
                Product.sku.ilike(term),
            )
        )


    # Same brand
    if brand:

        relevance_conditions.append(
            Product.brand.ilike(brand)
        )


    # --------------------------------------------------------
    # FIRST PASS: STRICTLY RELEVANT PRODUCTS
    # --------------------------------------------------------

    if relevance_conditions:

        relevant_query = query.filter(
            or_(
                *relevance_conditions
            )
        )

        relevant_products = (
            relevant_query
            .order_by(
                Product.featured.desc(),
                Product.stock.desc(),
                Product.created_at.desc(),
                Product.id.desc(),
            )
            .limit(
                RELATED_PRODUCTS_LIMIT
            )
            .all()
        )

    else:

        relevant_products = []


    # --------------------------------------------------------
    # RANK RESULTS IN PYTHON
    # --------------------------------------------------------

    def relevance_score(item):

        score = 0


        # Same category is strongest signal.
        if (
            category_id
            and item.category_id
            == category_id
        ):
            score += 100


        item_name = (
            item.name or ""
        ).lower()

        item_description = (
            item.description or ""
        ).lower()

        item_brand = (
            getattr(item, "brand", None)
            or ""
        ).lower()


        # Matching product terms.
        for word in search_words:

            if word in item_name:
                score += 25

            elif word in item_description:
                score += 8


        # Matching brand.
        if brand and item_brand == brand.lower():
            score += 20


        # Featured products.
        if getattr(item, "featured", False):
            score += 8


        # Available products receive a small boost.
        if (item.stock or 0) > 0:
            score += 5


        return score


    relevant_products.sort(
        key=lambda item: (
            relevance_score(item),
            item.created_at,
            item.id,
        ),
        reverse=True,
    )


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    related_products = []

    seen_ids = {
        product.id
    }

    for item in relevant_products:

        if item.id in seen_ids:
            continue

        seen_ids.add(item.id)

        related_products.append(item)

        if (
            len(related_products)
            >= RELATED_PRODUCTS_LIMIT
        ):
            break


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if len(related_products) < 4:

        remaining_limit = (
            RELATED_PRODUCTS_LIMIT
            - len(related_products)
        )

        existing_ids = list(
            seen_ids
        )


        fallback_query = (
            Product.query
            .options(
                joinedload(Product.category),
                selectinload(Product.images),
            )
            .filter(
                Product.is_active.is_(True),
                ~Product.id.in_(
                    existing_ids
                ),
            )
        )


        # Prefer same category if possible.
        if category_id:

            same_category_fallback = (
                fallback_query
                .filter(
                    Product.category_id
                    == category_id
                )
                .order_by(
                    Product.featured.desc(),
                    Product.stock.desc(),
                    Product.created_at.desc(),
                    Product.id.desc(),
                )
                .limit(
                    remaining_limit
                )
                .all()
            )

            related_products.extend(
                same_category_fallback
            )


        # If still short, use general products.
        if len(related_products) < RELATED_PRODUCTS_LIMIT:

            remaining_limit = (
                RELATED_PRODUCTS_LIMIT
                - len(related_products)
            )

            existing_ids = [
                item.id
                for item in related_products
            ]

            existing_ids.append(
                product.id
            )


            fallback_products = (
                Product.query
                .options(
                    joinedload(Product.category),
                    selectinload(Product.images),
                )
                .filter(
                    Product.is_active.is_(True),
                    ~Product.id.in_(
                        existing_ids
                    ),
                )
                .order_by(
                    Product.featured.desc(),
                    Product.stock.desc(),
                    Product.created_at.desc(),
                    Product.id.desc(),
                )
                .limit(
                    remaining_limit
                )
                .all()
            )

            related_products.extend(
                fallback_products
            )


    return related_products[
        :RELATED_PRODUCTS_LIMIT
    ]


def get_recently_viewed_products(
    recently_viewed_ids,
    current_product_id,
):
    """
    Retrieve recently viewed products while
    preserving session order.
    """

    recent_ids = [
        item
        for item in recently_viewed_ids
        if item != current_product_id
    ]


    if not recent_ids:
        return []


    recent_products = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.is_active.is_(True),
            Product.id.in_(recent_ids),
        )
        .all()
    )


    recent_lookup = {
        item.id: item
        for item in recent_products
    }


    recently_viewed = []

    for product_id in recent_ids:

        recent_product = (
            recent_lookup.get(
                product_id
            )
        )

        if recent_product:

            recently_viewed.append(
                recent_product
            )


    return recently_viewed[
        :RECENTLY_VIEWED_LIMIT
    ]


# ============================================================
# PRODUCT LISTING
# ============================================================

@product_bp.route("/")
def products():

    # --------------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------------

    params = get_listing_parameters()

    search = params["search"]
    min_price = params["min_price"]
    max_price = params["max_price"]
    min_price_value = params["min_price_value"]
    max_price_value = params["max_price_value"]
    stock_filter = params["stock_filter"]
    sort = params["sort"]
    page = params["page"]


    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category_id = request.args.get(
        "category",
        "",
        type=str,
    ).strip()

    selected_category = None


    if category_id:

        try:

            category_id_int = int(
                category_id
            )

            selected_category = (
                Category.query
                .filter(
                    Category.id
                    == category_id_int,

                    Category.is_active.is_(True),
                )
                .first()
            )


            if selected_category:

                category_id = str(
                    selected_category.id
                )

            else:

                category_id = ""


        except (
            ValueError,
            TypeError,
        ):

            category_id = ""


    # --------------------------------------------------------
    # QUERY
    # --------------------------------------------------------

    query = build_product_query()


    # Category filter for general /products route.
    if selected_category:

        query = query.filter(
            Product.category_id
            == selected_category.id
        )


    # Common filters.
    query = apply_listing_filters(
        query=query,
        search=search,
        min_price_value=min_price_value,
        max_price_value=max_price_value,
        stock_filter=stock_filter,
    )


    # Sorting.
    query = apply_sorting(
        query,
        sort,
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
    # WISHLIST
    # --------------------------------------------------------

    wishlist_product_ids = (
        get_wishlist_product_ids()
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

        wishlist_product_ids=wishlist_product_ids,
    )


# ============================================================
# SEO-FRIENDLY CATEGORY PAGE
# ============================================================

@product_bp.route(
    "/category/<string:slug>"
)
def category_products(slug):

    # --------------------------------------------------------
    # FIND ACTIVE CATEGORY
    # --------------------------------------------------------

    category = (
        Category.query
        .filter(
            Category.slug == slug,
            Category.is_active.is_(True),
        )
        .first_or_404()
    )


    # --------------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------------

    params = get_listing_parameters()

    search = params["search"]
    min_price = params["min_price"]
    max_price = params["max_price"]
    min_price_value = params["min_price_value"]
    max_price_value = params["max_price_value"]
    stock_filter = params["stock_filter"]
    sort = params["sort"]
    page = params["page"]


    # --------------------------------------------------------
    # CATEGORY QUERY
    # --------------------------------------------------------

    query = (
        build_product_query()
        .filter(
            Product.category_id
            == category.id
        )
    )


    # --------------------------------------------------------
    # SEARCH + PRICE + STOCK
    # --------------------------------------------------------

    query = apply_listing_filters(
        query=query,
        search=search,
        min_price_value=min_price_value,
        max_price_value=max_price_value,
        stock_filter=stock_filter,
    )


    # --------------------------------------------------------
    # SORTING
    # --------------------------------------------------------

    query = apply_sorting(
        query,
        sort,
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
    # WISHLIST
    # --------------------------------------------------------

    wishlist_product_ids = (
        get_wishlist_product_ids()
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

        search=search,

        category_id=str(
            category.id
        ),

        min_price=min_price,

        max_price=max_price,

        stock_filter=stock_filter,

        sort=sort,

        product_prices=product_prices,

        product_count=pagination.total,

        wishlist_product_ids=wishlist_product_ids,
    )


# ============================================================
# PRODUCT DETAILS
# ============================================================

@product_bp.route(
    "/<int:id>"
)
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
        abort(404)


    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    discounted_price = (
        get_discounted_price(
            product
        )
    )


    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    stock_status = (
        get_stock_status(
            product
        )
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


    # ========================================================
    # RELATED PRODUCTS
    # ========================================================

    related_products = (
        get_related_products(
            product
        )
    )


    # ========================================================
    # RELATED SEARCHES
    # ========================================================

    related_searches = (
        build_related_searches(
            product
        )
    )


    # ========================================================
    # RECENTLY VIEWED
    # ========================================================

    recently_viewed_ids = (
        get_recently_viewed_ids(
            product.id
        )
    )


    recently_viewed = (
        get_recently_viewed_products(
            recently_viewed_ids,
            product.id,
        )
    )


    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = product.category


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "product_details.html",

        product=product,

        category=category,

        discounted_price=discounted_price,

        stock_status=stock_status,

        is_in_wishlist=is_in_wishlist,

        related_products=related_products,

        related_searches=related_searches,

        recently_viewed=recently_viewed,
    )
