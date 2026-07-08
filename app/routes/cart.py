from flask import Blueprint, render_template

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/")
def cart():
    return render_template("cart.html")

@cart_bp.route("/checkout")
def checkout():
    return render_template("checkout.html")