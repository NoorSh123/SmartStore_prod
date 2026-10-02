import unittest
from unittest.mock import patch

from app import create_app
from extensions import db
from models.cart_item import CartItem
from models.order_item import OrderItem
from models.product import Product
from models.user import User
from services.ai_service import ai_search_service
from services.admin_product_ai_service import admin_product_ai_service


PRODUCT = {
    "name": "Audit Mouse",
    "description": "A comfortable mouse",
    "bullet_points": "Ergonomic design",
    "category": "Accessories",
    "tags": "mouse, ergonomic",
    "price": 25,
    "stock": 2,
}


class CoreFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "audit-only-test-key-with-adequate-length",
            "SECRET_KEY": "audit-only-test-key-with-adequate-length",
            "RATELIMIT_STORAGE_URI": "memory://",
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def token_for(self, email, role="user"):
        response = self.client.post("/auth/register", json={
            "full_name": "Test Person", "email": email, "password": "test-password"
        })
        self.assertEqual(response.status_code, 201)
        if role == "admin":
            user = User.query.filter_by(email=email).first()
            user.role = "admin"
            db.session.commit()
        response = self.client.post("/auth/login", json={
            "email": email, "password": "test-password"
        })
        self.assertEqual(response.status_code, 200)
        return response.json["access_token"]

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def create_product(self, admin_token, **changes):
        response = self.client.post(
            "/admin/products", headers=self.headers(admin_token),
            json={**PRODUCT, **changes},
        )
        self.assertEqual(response.status_code, 201)
        return response.json["product"]["id"]

    def test_authentication_and_invalid_json(self):
        token = self.token_for("auth@example.test")
        self.assertEqual(
            self.client.get("/auth/me", headers=self.headers(token)).status_code, 200
        )
        self.assertEqual(
            self.client.post("/auth/login", json={
                "email": "auth@example.test", "password": "wrong"
            }).status_code, 401
        )
        self.assertEqual(
            self.client.post("/auth/register", data="{broken",
                             content_type="application/json").status_code, 400
        )
        self.assertEqual(
            self.client.post("/auth/register", json={"email": []}).status_code, 400
        )
        self.assertEqual(
            self.client.post("/cart/add", headers=self.headers(token),
                             json={"product_id": 1, "quantity": "bad"}).status_code, 400
        )
        self.assertEqual(
            self.client.get("/", headers={
                "Origin": "https://unrelated.example"
            }).headers.get("Access-Control-Allow-Origin"), None
        )

    def test_backend_rbac(self):
        user = self.token_for("user@example.test")
        admin = self.token_for("admin@example.test", role="admin")
        self.assertEqual(
            self.client.post("/admin/products", headers=self.headers(user),
                             json=PRODUCT).status_code, 403
        )
        product_id = self.create_product(admin)
        self.assertEqual(
            self.client.patch(f"/admin/products/{product_id}",
                              headers=self.headers(user), json=PRODUCT).status_code, 403
        )
        self.assertEqual(
            self.client.delete(f"/admin/products/{product_id}",
                               headers=self.headers(user)).status_code, 403
        )

    def test_checkout_rechecks_stock_and_cannot_go_negative(self):
        user = self.token_for("buyer@example.test")
        admin = self.token_for("seller@example.test", role="admin")
        product_id = self.create_product(admin)
        self.assertEqual(
            self.client.post("/cart/add", headers=self.headers(user),
                             json={"product_id": product_id, "quantity": 2}).status_code,
            201,
        )
        self.assertEqual(
            self.client.patch(f"/admin/products/{product_id}",
                              headers=self.headers(admin),
                              json={**PRODUCT, "stock": 1}).status_code, 200
        )
        response = self.client.post("/orders/checkout", headers=self.headers(user))
        self.assertEqual(response.status_code, 409)
        db.session.expire_all()
        self.assertEqual(db.session.get(Product, product_id).stock, 1)
        self.assertEqual(CartItem.query.count(), 1)
        self.assertEqual(OrderItem.query.count(), 0)
        self.assertEqual(
            self.client.patch(f"/admin/products/{product_id}",
                              headers=self.headers(admin),
                              json=PRODUCT).status_code, 200
        )
        self.assertEqual(
            self.client.post("/orders/checkout",
                             headers=self.headers(user)).status_code, 201
        )
        db.session.expire_all()
        self.assertEqual(db.session.get(Product, product_id).stock, 0)

    def test_purchased_product_cannot_erase_order_history(self):
        user = self.token_for("history@example.test")
        admin = self.token_for("history-admin@example.test", role="admin")
        product_id = self.create_product(admin)
        self.client.post("/cart/add", headers=self.headers(user),
                         json={"product_id": product_id, "quantity": 1})
        self.assertEqual(
            self.client.post("/orders/checkout",
                             headers=self.headers(user)).status_code, 201
        )
        self.assertEqual(
            self.client.delete(f"/admin/products/{product_id}",
                               headers=self.headers(admin)).status_code, 409
        )
        orders = self.client.get("/orders", headers=self.headers(user)).json
        self.assertEqual(orders[0]["items"][0]["name"], PRODUCT["name"])
        self.assertEqual(OrderItem.query.count(), 1)
        unused_product_id = self.create_product(admin, name="Unused Mouse")
        self.assertEqual(
            self.client.delete(f"/admin/products/{unused_product_id}",
                               headers=self.headers(admin)).status_code, 200
        )

    def test_ai_requires_auth_and_enforces_limits(self):
        self.assertEqual(
            self.client.post("/ai/search", json={"query": "mouse"}).status_code, 401
        )
        self.assertEqual(
            self.client.post("/ai/chat", json={"messages": []}).status_code, 401
        )
        user = self.token_for("ai@example.test")
        with patch.object(ai_search_service, "interpret_search_query", return_value={
            "keywords": ["mouse"], "tags": [], "category": None
        }):
            for _ in range(5):
                self.assertEqual(
                    self.client.post("/ai/search", headers=self.headers(user),
                                     json={"query": "mouse"}).status_code, 200
                )
            self.assertEqual(
                self.client.post("/ai/search", headers=self.headers(user),
                                 json={"query": "mouse"}).status_code, 429
            )
        self.assertEqual(
            self.client.post("/ai/chat", headers=self.headers(user),
                             json={"messages": [{"role": "user",
                                                 "content": "x" * 1001}]}).status_code,
            400,
        )
        admin = self.token_for("ai-admin@example.test", role="admin")
        with patch.object(admin_product_ai_service, "interpret_product_request",
                          return_value={"status": "ready", "product": {}}):
            for _ in range(3):
                self.assertEqual(
                    self.client.post("/admin/ai-product/interpret",
                                     headers=self.headers(admin),
                                     json={"message": "mouse"}).status_code, 200
                )
            self.assertEqual(
                self.client.post("/admin/ai-product/interpret",
                                 headers=self.headers(admin),
                                 json={"message": "mouse"}).status_code, 429
            )


if __name__ == "__main__":
    unittest.main()
