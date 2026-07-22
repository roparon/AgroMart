from flask import Blueprint


# Main admin blueprint
admin_bp = Blueprint(
    "admin",
    __name__,
)


# Import admin route modules
# These modules all use the admin_bp defined above.
from app.routes.admin import dashboard
from app.routes.admin import products
from app.routes.admin import categories
from app.routes.admin import orders
from app.routes.admin import customers