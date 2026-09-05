from collections import defaultdict

from flask import Blueprint, render_template
from sqlalchemy.orm import joinedload, selectinload

from app.models.category import Category
from app.models.product import Product
from app.models.homepage_content import HomepageContent


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    """
    Bomet Machineries Ltd. homepage.

    Loads:
    - Active CMS homepage content
    - Active product categories
    - Up to 6 active/featured products per category

    The queries use eager loading to reduce database round-trips
    when accessing product categories and product images.
    """

    # ==========================================================
    # 1. HOMEPAGE CMS CONTENT
    # ==========================================================

    homepage_items = (
        HomepageContent.query
        .filter(
            HomepageContent.is_active.is_(True)
        )
        .order_by(
            HomepageContent.sort_order.asc(),
            HomepageContent.id.asc(),
        )
        .all()
    )

    # Convert:
    #
    # [
    #     HomepageContent(key="hero_1"),
    #     HomepageContent(key="hero_2"),
    # ]
    #
    # into:
    #
    # {
    #     "hero_1": HomepageContent(...),
    #     "hero_2": HomepageContent(...),
    # }

    cms = {
        item.key: item
        for item in homepage_items
    }

    # ==========================================================
    # 2. ACTIVE CATEGORIES
    # ==========================================================

    categories = (
        Category.query
        .filter(
            Category.is_active.is_(True)
        )
        .order_by(
            Category.name.asc()
        )
        .all()
    )

    # ==========================================================
    # 3. HOMEPAGE PRODUCT POOL
    # ==========================================================
    #
    # Instead of running a separate query for every category,
    # fetch one controlled pool of products.
    #
    # joinedload(Product.category)
    #     -> loads the product's category together with the
    #        product query.
    #
    # selectinload(Product.images)
    #     -> loads product images efficiently in a second
    #        controlled query rather than one query per product.
    #
    # 60 products gives the homepage enough data to populate
    # multiple categories without loading the entire catalog.
    #

    homepage_products = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.images),
        )
        .filter(
            Product.is_active.is_(True),
        )
        .order_by(
            Product.featured.desc(),
            Product.created_at.desc(),
        )
        .limit(60)
        .all()
    )

    # ==========================================================
    # 4. GROUP PRODUCTS BY CATEGORY
    # ==========================================================

    featured_by_category = defaultdict(list)

    for product in homepage_products:

        category_id = product.category_id

        # Ignore products without a category.
        if not category_id:
            continue

        # Maximum 6 products per category.
        if len(featured_by_category[category_id]) >= 6:
            continue

        featured_by_category[category_id].append(product)

    # Convert defaultdict to normal dict before sending it
    # to Jinja.
    featured_by_category = dict(featured_by_category)

    # ==========================================================
    # 5. RENDER HOMEPAGE
    # ==========================================================

    return render_template(
        "index.html",
        cms=cms,
        categories=categories,
        featured_by_category=featured_by_category,
    )