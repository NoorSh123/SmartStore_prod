from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from extensions import db, jwt, limiter


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    CORS(app, origins=app.config["CORS_ORIGINS"])

    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    from routes.product_routes import product_bp
    from routes.auth_routes import auth_bp
    from routes.cart_routes import cart_bp
    from routes.order_routes import order_bp
    from routes.ai_routes import ai_bp
    from routes.admin_routes import admin_bp

    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp)

    @app.route("/")
    def home():
        return {"message": "SmartStore backend is running"}

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Request body is too large"}), 413

    @app.errorhandler(429)
    def too_many_requests(_error):
        return jsonify({"error": "Too many requests. Please try again later"}), 429

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
