from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models.cart_item import CartItem
from models.product import Product
from routes.validation import json_object, positive_int

cart_bp = Blueprint("cart_bp", __name__, url_prefix="/cart")


@cart_bp.route("", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = int(get_jwt_identity())

    cart_items = CartItem.query.filter_by(user_id=user_id).all()

    result = []
    total_price = 0

    for item in cart_items:
        product_total = item.quantity * item.product.price
        total_price += product_total

        result.append({
            "id": item.id,
            "product_id": item.product.id,
            "name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
            "stock": item.product.stock,
            "item_total": product_total
        })

    return jsonify({
        "items": result,
        "total_price": total_price
    }), 200


@cart_bp.route("/add", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = int(get_jwt_identity())
    data, error = json_object()
    if error:
        return error

    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not positive_int(product_id) or not positive_int(quantity):
        return jsonify({"error": "product_id and quantity must be positive integers"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product.stock < quantity:
        return jsonify({"error": "Not enough stock available"}), 400

    existing_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()

    if existing_item:
        new_quantity = existing_item.quantity + quantity

        if new_quantity > product.stock:
            return jsonify({"error": "Requested quantity exceeds stock"}), 400

        existing_item.quantity = new_quantity
    else:
        new_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(new_item)

    db.session.commit()

    return jsonify({"message": "Product added to cart"}), 201


@cart_bp.route("/update", methods=["PUT"])
@jwt_required()
def update_cart_item():
    user_id = int(get_jwt_identity())
    data, error = json_object()
    if error:
        return error

    cart_item_id = data.get("cart_item_id")
    quantity = data.get("quantity")

    if not positive_int(cart_item_id) or not positive_int(quantity):
        return jsonify({"error": "cart_item_id and quantity must be positive integers"}), 400

    cart_item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first()
    if not cart_item:
        return jsonify({"error": "Cart item not found"}), 404

    if quantity > cart_item.product.stock:
        return jsonify({"error": "Requested quantity exceeds stock"}), 400

    cart_item.quantity = quantity
    db.session.commit()

    return jsonify({"message": "Cart item updated"}), 200


@cart_bp.route("/remove/<int:cart_item_id>", methods=["DELETE"])
@jwt_required()
def remove_cart_item(cart_item_id):
    user_id = int(get_jwt_identity())

    cart_item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first()
    if not cart_item:
        return jsonify({"error": "Cart item not found"}), 404

    db.session.delete(cart_item)
    db.session.commit()

    return jsonify({"message": "Cart item removed"}), 200
