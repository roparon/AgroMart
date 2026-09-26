from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Blueprint, Response, url_for

from app.models.product import Product
from app.models.category import Category


seo_bp = Blueprint("seo", __name__)


# ============================================================
# GOOGLE / SEARCH ENGINE SITEMAP
# ============================================================

@seo_bp.route("/sitemap.xml")
def sitemap():
    """
    Dynamic XML sitemap for Google and other search engines.

    Includes:
        - Homepage
        - Product listing
        - Active categories
        - Active products

    Excludes:
        - Admin pages
        - Authentication pages
        - Cart / checkout
        - Orders
        - Wishlist
        - POST-only actions
    """

    urlset = Element(
        "urlset",
        {
            "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"
        },
    )

    def add_url(location, lastmod=None, changefreq=None, priority=None):
        url_element = SubElement(urlset, "url")

        loc_element = SubElement(url_element, "loc")
        loc_element.text = location

        if lastmod:
            lastmod_element = SubElement(url_element, "lastmod")
            lastmod_element.text = lastmod

        if changefreq:
            changefreq_element = SubElement(url_element, "changefreq")
            changefreq_element.text = changefreq

        if priority:
            priority_element = SubElement(url_element, "priority")
            priority_element.text = priority

    def format_lastmod(value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.date().isoformat()

        return str(value)[:10]

    # ========================================================
    # HOMEPAGE
    # ========================================================

    add_url(
        url_for("home.home", _external=True),
        changefreq="weekly",
        priority="1.0",
    )

    # ========================================================
    # PRODUCT LISTING
    # ========================================================

    add_url(
        url_for("product.products", _external=True),
        changefreq="daily",
        priority="0.9",
    )

    # ========================================================
    # ACTIVE CATEGORIES
    # ========================================================

    categories = (
        Category.query
        .filter(Category.is_active.is_(True))
        .order_by(Category.id.asc())
        .all()
    )

    for category in categories:
        add_url(
            url_for(
                "product.category_products",
                slug=category.slug,
                _external=True,
            ),
            lastmod=format_lastmod(category.updated_at),
            changefreq="weekly",
            priority="0.8",
        )

    # ========================================================
    # ACTIVE PRODUCTS
    # ========================================================

    products = (
        Product.query
        .filter(Product.is_active.is_(True))
        .order_by(Product.id.asc())
        .all()
    )

    for product in products:
        add_url(
            url_for(
                "product.product_details",
                id=product.id,
                _external=True,
            ),
            lastmod=format_lastmod(product.updated_at),
            changefreq="weekly",
            priority="0.7",
        )

    # ========================================================
    # XML RESPONSE
    # ========================================================

    xml = tostring(
        urlset,
        encoding="utf-8",
        xml_declaration=True,
    )

    return Response(
        xml,
        mimetype="application/xml",
    )


# ============================================================
# ROBOTS.TXT
# ============================================================

@seo_bp.route("/robots.txt")
def robots():
    """
    Tell search engines which public areas can be crawled
    and where the sitemap is located.
    """

    sitemap_url = url_for(
        "seo.sitemap",
        _external=True,
    )

    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /auth/
Disallow: /cart/
Disallow: /wishlist/

Sitemap: {sitemap_url}
"""

    return Response(
        content,
        mimetype="text/plain",
    )
