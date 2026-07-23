from flask import Blueprint


admin_bp = Blueprint("admin", __name__,)


from app.routes.admin.products import products_bp
from app.routes.admin.categories import categories_bp
from app.routes.admin.orders import orders_bp
from app.routes.admin.customers import customers_bp