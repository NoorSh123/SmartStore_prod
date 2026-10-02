import { useEffect, useState } from "react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

function HomePage() {
  const [products, setProducts] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { user } = useAuth();

  const loadAllProducts = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/products");
      setProducts(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load products");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllProducts();
  }, []);

  const handleSearch = async () => {
    const cleanedSearch = searchText.trim();

    if (!cleanedSearch) {
      loadAllProducts();
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await api.get("/products/search", {
        params: { query: cleanedSearch }
      });

      setProducts(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchText("");
    loadAllProducts();
  };

  const handleAddToCart = async (productId) => {
    try {
      await api.post("/cart/add", {
        product_id: productId,
        quantity: 1
      });
      alert("Product added to cart");
    } catch (err) {
      alert(err.response?.data?.error || "Failed to add product to cart");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>SmartStore Products</h1>

      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="Search products by keyword..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{
            padding: "10px",
            width: "300px",
            marginRight: "10px"
          }}
        />

        <button onClick={handleSearch} disabled={loading} style={{ marginRight: "10px" }}>
          {loading ? "Searching..." : "Search"}
        </button>

        <button onClick={handleClearSearch} disabled={loading}>
          Clear
        </button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        products.map((product) => (
          <div
            key={product.id}
            style={{
              border: "1px solid #ccc",
              padding: "15px",
              marginBottom: "15px",
              borderRadius: "8px"
            }}
          >
            <h2>{product.name}</h2>
            <p>{product.description}</p>
            <p><strong>Category:</strong> {product.category}</p>
            <p><strong>Tags:</strong> {product.tags}</p>
            <p><strong>Price:</strong> ₪{product.price}</p>
            <p><strong>Stock:</strong> {product.stock}</p>

            {user && (
              <button onClick={() => handleAddToCart(product.id)}>
                Add to Cart
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default HomePage;