from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.cart_item import CartItem
from models.order import Order
from models.order_item import OrderItem
from models.product import Product

order_bp = Blueprint("order_bp", __name__, url_prefix="/orders")


@order_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout():
    user_id = int(get_jwt_identity())
    try:
        # InnoDB locks these rows until commit so two checkouts cannot use the
        # same cart or the same remaining stock concurrently.
        cart_items = (
            CartItem.query.filter_by(user_id=user_id)
            .order_by(CartItem.id).with_for_update().all()
        )
        if not cart_items:
            db.session.rollback()
            return jsonify({"error": "Cart is empty"}), 400

        product_ids = sorted({item.product_id for item in cart_items})
        products = {
            product.id: product
            for product in db.session.execute(
                db.select(Product)
                .where(Product.id.in_(product_ids))
                .order_by(Product.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalars()
        }
        for item in cart_items:
            product = products.get(item.product_id)
            if not product or item.quantity < 1 or product.stock < item.quantity:
                db.session.rollback()
                return jsonify({"error": "Insufficient stock for a cart item"}), 409

        total_price = sum(
            item.quantity * products[item.product_id].price for item in cart_items
        )
        order = Order(user_id=user_id, total_price=total_price, status="created")
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            product = products[item.product_id]
            result = db.session.execute(
                db.update(Product)
                .where(Product.id == product.id, Product.stock >= item.quantity)
                .values(stock=Product.stock - item.quantity)
            )
            if result.rowcount != 1:
                db.session.rollback()
                return jsonify({"error": "Insufficient stock for a cart item"}), 409
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price
            ))

        CartItem.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({
            "message": "Order created successfully",
            "order_id": order.id
        }), 201
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "Checkout is temporarily unavailable"}), 503


@order_bp.route("", methods=["GET"])
@jwt_required()
def get_orders():

    user_id = int(get_jwt_identity())

    orders = Order.query.filter_by(user_id=user_id).all()

    result = []

    for order in orders:

        items = []

        for item in order.order_items:
            items.append({
                "product_id": item.product_id,
                "name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price
            })

        result.append({
            "order_id": order.id,
            "total_price": order.total_price,
            "status": order.status,
            "created_at": order.created_at,
            "items": items
        })

    return jsonify(result), 200
