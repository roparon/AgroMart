from app import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)
    discount = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    sku = db.Column(db.String(100), unique=True)
    slug = db.Column(db.String(255), unique=True)
    images = db.relationship("ProductImage", backref="product", lazy=True, cascade="all, delete-orphan")    
    featured = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Product {self.name}>"