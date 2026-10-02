from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import get_jwt_identity, jwt_required

from models.product import Product
from models.user import User
from services.ai_service import ai_search_service
from extensions import limiter
from routes.validation import json_object

ai_bp = Blueprint("ai_bp", __name__, url_prefix="/ai")


def ai_limit_exceeded(limit):
    return make_response(
        jsonify({
            "error": "AI request limit reached. Please try again later."
        }),
        429
    )


@ai_bp.route("/search", methods=["POST"])
@jwt_required()
@limiter.limit("5 per hour; 20 per day", key_func=get_jwt_identity, on_breach=ai_limit_exceeded)
def ai_search():
    data, error = json_object()
    if error:
        return error
    query = data.get("query")

    if not isinstance(query, str) or not query.strip() or len(query) > 300:
        return jsonify({"error": "query must contain 1 to 300 characters"}), 400
    query = query.strip()

    interpreted = ai_search_service.interpret_search_query(query)

    keywords = interpreted.get("keywords", [])
    tags = interpreted.get("tags", [])
    category = interpreted.get("category")

    search_terms = []

    for keyword in keywords:
        if keyword and keyword not in search_terms:
            search_terms.append(keyword)

    for tag in tags:
        if tag and tag not in search_terms:
            search_terms.append(tag)

    products = Product.query.all()

    scored_results = []

    for product in products:
        score = 0

        name_text = (product.name or "").lower()
        description_text = (product.description or "").lower()
        tags_text = (product.tags or "").lower()
        category_text = (product.category or "").lower()
        bullet_points_text = (product.bullet_points or "").lower()

        if category and category in category_text:
            score += 5

        for term in search_terms:
            if term in name_text:
                score += 5

            if term in tags_text:
                score += 4

            if term in category_text:
                score += 3

            if term in description_text:
                score += 2

            if term in bullet_points_text:
                score += 2

        if score > 0:
            scored_results.append({
                "score": score,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "bullet_points": product.bullet_points,
                    "category": product.category,
                    "tags": product.tags,
                    "price": product.price,
                    "stock": product.stock
                }
            })

    scored_results.sort(key=lambda item: item["score"], reverse=True)

    results = [item["product"] for item in scored_results]

    return jsonify({
        "query": query,
        "interpreted": interpreted,
        "count": len(results),
        "products": results
    }), 200


@ai_bp.route("/chat", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour; 30 per day", key_func=get_jwt_identity, on_breach=ai_limit_exceeded)
def ai_chat():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role == "admin":
        return jsonify({"error": "Only normal users can use the AI assistant"}), 403

    data, error = json_object()
    if error:
        return error
    messages = data.get("messages")

    if not isinstance(messages, list) or not 1 <= len(messages) <= 10:
        return jsonify({"error": "messages must contain 1 to 10 entries"}), 400
    if any(
        not isinstance(message, dict)
        or message.get("role") not in {"user", "assistant"}
        or not isinstance(message.get("content"), str)
        or not message["content"].strip()
        or len(message["content"]) > 1000
        for message in messages
    ) or sum(len(message["content"]) for message in messages) > 6000:
        return jsonify({"error": "Invalid or oversized chat message"}), 400

    latest_message = ""

    for message in reversed(messages):
        if message["role"] == "user":
            latest_message = message["content"].strip()
            break

    if not latest_message:
        return jsonify({"error": "message is required"}), 400

    search_text = _build_search_text(messages, latest_message)
    interpreted = ai_search_service.interpret_search_query(search_text)
    products = _find_matching_products(interpreted)
    chat_result = ai_search_service.chat_about_products(messages, products)

    return jsonify({
        "reply": chat_result.get("reply"),
        "interpreted": interpreted,
        "count": len(products),
        "products": products,
        "_meta": chat_result.get("_meta", {})
    }), 200


def _find_matching_products(interpreted):
    keywords = interpreted.get("keywords", [])
    tags = interpreted.get("tags", [])
    category = interpreted.get("category")

    search_terms = []

    for keyword in keywords:
        if keyword and keyword not in search_terms:
            search_terms.append(keyword)

    for tag in tags:
        if tag and tag not in search_terms:
            search_terms.append(tag)

    products = Product.query.all()
    required_terms = _find_required_terms(products, search_terms)
    scored_results = []

    for product in products:
        score = 0

        name_text = (product.name or "").lower()
        description_text = (product.description or "").lower()
        tags_text = (product.tags or "").lower()
        category_text = (product.category or "").lower()
        bullet_points_text = (product.bullet_points or "").lower()
        strong_text = " ".join([name_text, category_text, tags_text])

        if required_terms and not any(term in strong_text for term in required_terms):
            continue

        if category and category in category_text:
            score += 5

        for term in search_terms:
            if term in name_text:
                score += 5

            if term in tags_text:
                score += 4

            if term in category_text:
                score += 3

            if term in description_text:
                score += 2

            if term in bullet_points_text:
                score += 2

        if score > 0:
            scored_results.append({
                "score": score,
                "product": _serialize_product(product)
            })

    scored_results.sort(key=lambda item: item["score"], reverse=True)

    return [item["product"] for item in scored_results[:8]]


def _find_required_terms(products, search_terms):
    required_terms = []

    for term in search_terms:
        for product in products:
            name_text = (product.name or "").lower()
            category_text = (product.category or "").lower()

            if term in name_text or term in category_text:
                required_terms.append(term)
                break

    return required_terms


def _build_search_text(messages, latest_message):
    user_messages = []

    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue

        content = (message.get("content") or "").strip()

        if content:
            user_messages.append(content)

    if not user_messages:
        return latest_message

    return " ".join(user_messages[-4:])


def _serialize_product(product):
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
