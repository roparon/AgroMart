from app import db


class Wishlist(db.Model):
    __tablename__ = "wishlist"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    product = db.relationship(
        "Product",
        backref="wishlist_items"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_wishlist_user_product"
        ),
    )

    def __repr__(self):
        return (
            f"<Wishlist user={self.user_id} "
            f"product={self.product_id}>"
        )