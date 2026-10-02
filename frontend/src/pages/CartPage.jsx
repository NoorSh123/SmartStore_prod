import { useEffect, useState } from "react";
import api from "../services/api";

function CartPage() {
  const [cart, setCart] = useState({ items: [], total_price: 0 });
  const [error, setError] = useState("");

  const loadCart = async () => {
    try {
      const response = await api.get("/cart");
      setCart(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load cart");
    }
  };

  useEffect(() => {
    loadCart();
  }, []);

  const handleQuantityChange = async (cartItemId, quantity) => {
    try {
      await api.put("/cart/update", {
        cart_item_id: cartItemId,
        quantity: Number(quantity)
      });
      loadCart();
    } catch (err) {
      alert(err.response?.data?.error || "Failed to update cart item");
    }
  };

  const handleRemove = async (cartItemId) => {
    try {
      await api.delete(`/cart/remove/${cartItemId}`);
      loadCart();
    } catch (err) {
      alert(err.response?.data?.error || "Failed to remove cart item");
    }
  };

  const handleCheckout = async () => {
    try {
      const response = await api.post("/orders/checkout");
      alert("Order created. Order ID: " + response.data.order_id);
      loadCart();
    } catch (err) {
      alert(err.response?.data?.error || "Checkout failed");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Your Cart</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {cart.items.length === 0 ? (
        <p>Your cart is empty.</p>
      ) : (
        <>
          {cart.items.map((item) => (
            <div
              key={item.id}
              style={{
                border: "1px solid #ccc",
                padding: "15px",
                marginBottom: "15px",
                borderRadius: "8px"
              }}
            >
              <h3>{item.name}</h3>
              <p>Price: ₪{item.price}</p>
              <p>Item Total: ₪{item.item_total}</p>

              <label>
                Quantity:
                <input
                  type="number"
                  min="1"
                  value={item.quantity}
                  onChange={(e) =>
                    handleQuantityChange(item.id, e.target.value)
                  }
                  style={{ marginLeft: "10px", width: "60px" }}
                />
              </label>

              <div style={{ marginTop: "10px" }}>
                <button onClick={() => handleRemove(item.id)}>Remove</button>
              </div>
            </div>
          ))}

          <h2>Total: ₪{cart.total_price}</h2>

          <button onClick={handleCheckout}>
            Checkout
          </button>
        </>
      )}
    </div>
  );
}

export default CartPage;