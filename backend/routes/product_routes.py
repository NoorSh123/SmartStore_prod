from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from models.product import Product

product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/products", methods=["GET"])
def get_products():
    products = Product.query.all()

    result = []
    for product in products:
        result.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "bullet_points": product.bullet_points,
            "category": product.category,
            "tags": product.tags,
            "price": product.price,
            "stock": product.stock
        })

    return jsonify(result), 200


@product_bp.route("/products/search", methods=["GET"])
def search_products():
    query_text = (request.args.get("query") or "").strip()

    if not query_text:
        return jsonify([]), 200

    search_terms = []
    for term in query_text.lower().split():
        cleaned = term.strip()
        if cleaned and cleaned not in search_terms:
            search_terms.append(cleaned)

    db_query = Product.query

    filters = []
    for term in search_terms:
        filters.append(Product.name.ilike(f"%{term}%"))
        filters.append(Product.description.ilike(f"%{term}%"))
        filters.append(Product.tags.ilike(f"%{term}%"))
        filters.append(Product.category.ilike(f"%{term}%"))
        filters.append(Product.bullet_points.ilike(f"%{term}%"))

    products = db_query.filter(or_(*filters)).all()

    result = []
    for product in products:
        result.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "bullet_points": product.bullet_points,
            "category": product.category,
            "tags": product.tags,
            "price": product.price,
            "stock": product.stock
        })

    return jsonify(result), 200