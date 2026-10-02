import json
import math

from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db, limiter
from models.user import User
from models.product import Product
from models.order_item import OrderItem
from routes.validation import json_object
from services.admin_product_ai_service import admin_product_ai_service

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")


def ai_limit_exceeded(limit):
    return make_response(
        jsonify({
            "error": "Your allowed AI usage has been used for today."
        }),
        429
    )


def get_current_admin():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user or user.role != "admin":
        return None

    return user


def serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "bullet_points": product.bullet_points,
        "category": product.category,
        "tags": product.tags,
        "price": product.price,
        "stock": product.stock
    }


def split_csv_text(value):
    if value is None:
        return []

    if not isinstance(value, str):
        return []

    parts = [item.strip() for item in value.split(",")]
    return [item for item in parts if item]


def normalize_list_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        cleaned = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped and stripped not in cleaned:
                    cleaned.append(stripped)
        return ", ".join(cleaned)

    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",")]
        cleaned = []
        for item in parts:
            if item and item not in cleaned:
                cleaned.append(item)
        return ", ".join(cleaned)

    return ""


def parse_and_validate_product_payload(data):
    for field in ("name", "description", "category"):
        if not isinstance(data.get(field), str):
            return None, f"{field} must be text"
    name = data["name"].strip()
    description = data["description"].strip()
    bullet_points = normalize_list_text(data.get("bullet_points"))
    category = data["category"].strip()
    tags = normalize_list_text(data.get("tags"))
    price = data.get("price")
    stock = data.get("stock")

    if not name:
        return None, "name is required"

    if not description:
        return None, "description is required"

    if not bullet_points:
        return None, "bullet_points are required"

    if not category:
        return None, "category is required"

    if not tags:
        return None, "tags are required"
    if len(name) > 150 or len(category) > 100:
        return None, "name or category is too long"

    if price is None or price == "":
        return None, "price is required"

    if stock is None or stock == "":
        return None, "stock is required"

    try:
        if isinstance(price, bool):
            raise TypeError
        price = float(price)
    except (ValueError, TypeError):
        return None, "price must be a valid number"

    try:
        if isinstance(stock, bool) or (isinstance(stock, float) and not stock.is_integer()):
            raise TypeError
        stock = int(stock)
    except (ValueError, TypeError):
        return None, "stock must be a valid integer"

    if not math.isfinite(price) or price < 0:
        return None, "price must be a finite nonnegative number"

    if stock < 0:
        return None, "stock cannot be negative"

    parsed = {
        "name": name,
        "description": description,
        "bullet_points": bullet_points,
        "category": category,
        "tags": tags,
        "price": price,
        "stock": stock
    }

    return parsed, None


@admin_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    data, error = json_object()
    if error:
        return error
    parsed, error = parse_and_validate_product_payload(data)

    if error:
        return jsonify({"error": error}), 400

    new_product = Product(
        name=parsed["name"],
        description=parsed["description"],
        bullet_points=parsed["bullet_points"],
        category=parsed["category"],
        tags=parsed["tags"],
        price=parsed["price"],
        stock=parsed["stock"]
    )

    db.session.add(new_product)
    db.session.commit()

    return jsonify({
        "message": "Product created successfully",
        "product": serialize_product(new_product)
    }), 201


@admin_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    product = Product.query.get(product_id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(serialize_product(product)), 200


@admin_bp.route("/products/<int:product_id>", methods=["PATCH"])
@jwt_required()
def update_product(product_id):
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    data, error = json_object()
    if error:
        return error
    parsed, error = parse_and_validate_product_payload(data)

    if error:
        return jsonify({"error": error}), 400

    product = db.session.execute(
        db.select(Product).where(Product.id == product_id).with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    product.name = parsed["name"]
    product.description = parsed["description"]
    product.bullet_points = parsed["bullet_points"]
    product.category = parsed["category"]
    product.tags = parsed["tags"]
    product.price = parsed["price"]
    product.stock = parsed["stock"]

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully",
        "product": serialize_product(product)
    }), 200


@admin_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    product = db.session.execute(
        db.select(Product).where(Product.id == product_id).with_for_update()
    ).scalar_one_or_none()

    if not product:
        return jsonify({"error": "Product not found"}), 404
    if OrderItem.query.filter_by(product_id=product_id).first():
        db.session.rollback()
        return jsonify({"error": "Product is part of order history and cannot be deleted"}), 409

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": "Product deleted successfully"}), 200


@admin_bp.route("/products/<int:product_id>/ai-improve", methods=["POST"])
@jwt_required()
@limiter.limit("3 per day", key_func=get_jwt_identity, on_breach=ai_limit_exceeded)
def ai_improve_product(product_id):
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    product = Product.query.get(product_id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    current_draft = {
        "name": product.name,
        "description": product.description,
        "bullet_points": split_csv_text(product.bullet_points),
        "category": product.category,
        "tags": split_csv_text(product.tags),
        "price": product.price,
        "stock": product.stock
    }

    result = admin_product_ai_service.interpret_product_request(
        admin_message="Improve this product listing. Make it clearer, stronger, and more professional without inventing facts. Keep the existing price and stock.",
        current_draft=current_draft
    )
    if result.get("_meta", {}).get("source") != "openai":
        return jsonify({"error": "AI improvement is currently unavailable"}), 503

    suggested_product = result.get("product", {}) if isinstance(result, dict) else {}

    improved_product = {
        "name": suggested_product.get("name") or product.name,
        "description": suggested_product.get("description") or product.description,
        "bullet_points": normalize_list_text(suggested_product.get("bullet_points")) or product.bullet_points,
        "category": suggested_product.get("category") or product.category,
        "tags": normalize_list_text(suggested_product.get("tags")) or product.tags,
        "price": product.price,
        "stock": product.stock
    }

    return jsonify({
        "status": "ready",
        "product": improved_product
    }), 200


@admin_bp.route("/ai-product/interpret", methods=["POST"])
@jwt_required()
@limiter.limit("3 per day", key_func=get_jwt_identity, on_breach=ai_limit_exceeded)
def interpret_ai_product():
    admin_user = get_current_admin()

    if not admin_user:
        return jsonify({"error": "Admin access required"}), 403

    data, error = json_object()
    if error:
        return error

    message = data.get("message", "")
    current_draft = data.get("current_draft", {})
    if not isinstance(message, str) or len(message) > 2000 or not isinstance(current_draft, dict):
        return jsonify({"error": "Invalid AI product request"}), 400
    if len(json.dumps(current_draft)) > 6000:
        return jsonify({"error": "Product draft is too large"}), 400

    result = admin_product_ai_service.interpret_product_request(
        admin_message=message,
        current_draft=current_draft
    )

    return jsonify(result), 200
