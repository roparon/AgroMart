from collections import defaultdict

from flask import Blueprint, render_template, request
from sqlalchemy.orm import joinedload, selectinload

from app.models.category import Category
from app.models.product import Product
from app.models.homepage_content import HomepageContent
from app.models.homepage_section import HomepageSection
from app.models.homepage_setting import HomepageSetting


home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    """
    Public homepage for Bomet Machineries Ltd.

    Loads:
    - Homepage settings
    - Published homepage sections
    - Published legacy homepage content
    - Active categories
    - Featured/active products grouped by category

    Administrators may use ?preview=1 to preview unpublished
    homepage sections/content.
    """

    # ==========================================================
    # 1. PREVIEW MODE
    # ==========================================================

    preview = (
        request.args.get("preview", "").lower()
        in {"1", "true", "yes", "on"}
    )

    # Only administrators can use preview mode.
    if preview:
        from flask_login import current_user

        if (
            not current_user.is_authenticated
            or not current_user.is_admin
        ):
            preview = False

    # ==========================================================
    # 2. HOMEPAGE SETTINGS
    # ==========================================================

    settings = (
        HomepageSetting.query
        .filter(
            HomepageSetting.is_active.is_(True)
        )
        .first()
    )

    # If no active settings exist, create a safe fallback object
    # for the template without writing anything to the database.
    if settings is None:
        settings = HomepageSetting(
            site_title="Bomet Machineries Ltd.",
            is_active=True,
            announcement_active=False,
        )

    # ==========================================================
    # 3. HOMEPAGE SECTIONS
    # ==========================================================

    sections_query = (
        HomepageSection.query
        .order_by(
            HomepageSection.sort_order.asc(),
            HomepageSection.id.asc(),
        )
    )

    if not preview:
        sections_query = sections_query.filter(
            HomepageSection.is_active.is_(True)
        )

    sections = sections_query.all()

    # ==========================================================
    # 4. LEGACY HOMEPAGE CONTENT
    # ==========================================================
    #
    # Keep the old HomepageContent system available so existing
    # homepage content does not suddenly disappear.
    #

    content_query = (
        HomepageContent.query
        .order_by(
            HomepageContent.sort_order.asc(),
            HomepageContent.id.asc(),
        )
    )

    if not preview:
        content_query = content_query.filter(
            HomepageContent.is_active.is_(True)
        )

    homepage_items = content_query.all()

    cms = {
        item.key: item
        for item in homepage_items
    }

    # ==========================================================
    # 5. ACTIVE CATEGORIES
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
    # 6. HOMEPAGE PRODUCT POOL
    # ==========================================================
    #
    # Fetch a controlled pool instead of querying separately for
    # every category.
    #
    # joinedload(Product.category)
    #     Loads the product category efficiently.
    #
    # selectinload(Product.images)
    #     Loads product images in a separate efficient query.
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
    # 7. GROUP PRODUCTS BY CATEGORY
    # ==========================================================

    featured_by_category = defaultdict(list)

    for product in homepage_products:

        category_id = product.category_id

        # Ignore products without a category.
        if not category_id:
            continue

        # Maximum 6 products per category.
        if len(
            featured_by_category[category_id]
        ) >= 6:
            continue

        featured_by_category[
            category_id
        ].append(product)

    featured_by_category = dict(
        featured_by_category
    )

    # ==========================================================
    # 8. PRODUCTS BY CATEGORY NAME
    # ==========================================================
    #
    # This is useful for CMS sections that refer to a category
    # by slug/name through their JSON config.
    #

    featured_categories = {}

    for category in categories:
        featured_categories[
            category.id
        ] = featured_by_category.get(
            category.id,
            [],
        )

    # ==========================================================
    # 9. RENDER HOMEPAGE
    # ==========================================================

    return render_template(
        "index.html",

        # New CMS system
        settings=settings,
        sections=sections,

        # Legacy CMS system
        cms=cms,
        homepage_items=homepage_items,

        # Catalog data
        categories=categories,
        homepage_products=homepage_products,
        featured_by_category=featured_by_category,
        featured_categories=featured_categories,

        # Preview state
        preview=preview,
    )