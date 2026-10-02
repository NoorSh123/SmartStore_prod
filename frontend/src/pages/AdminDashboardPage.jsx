import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function AdminDashboardPage() {
  const navigate = useNavigate();

  const [products, setProducts] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [error, setError] = useState("");

  const loadAllProducts = async () => {
    try {
      setLoadingProducts(true);
      setError("");

      const response = await api.get("/products");
      setProducts(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load products");
    } finally {
      setLoadingProducts(false);
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
      setLoadingProducts(true);
      setError("");

      const response = await api.get("/products/search", {
        params: { query: cleanedSearch }
      });

      setProducts(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Search failed");
    } finally {
      setLoadingProducts(false);
    }
  };

  const handleClearSearch = () => {
    setSearchText("");
    loadAllProducts();
  };

  const handleDeleteProduct = async (productId) => {
    const confirmed = window.confirm("Are you sure you want to delete this product?");

    if (!confirmed) {
      return;
    }

    try {
      await api.delete(`/admin/products/${productId}`);

      setProducts((prev) => prev.filter((product) => product.id !== productId));
    } catch (err) {
      setError(err.response?.data?.error || "Failed to delete product");
    }
  };

  const handleEditProduct = (productId) => {
    navigate(`/admin/products/${productId}/edit`);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Admin Home</h1>
      <p>Search, review, edit, and delete products.</p>

      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="Search products by keyword..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ padding: "10px", width: "300px", marginRight: "10px" }}
        />

        <button onClick={handleSearch} disabled={loadingProducts} style={{ marginRight: "10px" }}>
          {loadingProducts ? "Searching..." : "Search"}
        </button>

        <button onClick={handleClearSearch} disabled={loadingProducts}>
          Clear
        </button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loadingProducts && products.length === 0 ? (
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
            <p><strong>Bullet Points:</strong> {product.bullet_points}</p>
            <p><strong>Price:</strong> ₪{product.price}</p>
            <p><strong>Stock:</strong> {product.stock}</p>

            <button
              onClick={() => handleEditProduct(product.id)}
              style={{ marginRight: "10px" }}
            >
              Edit Product
            </button>

            <button onClick={() => handleDeleteProduct(product.id)}>
              Delete Product
            </button>
          </div>
        ))
      )}
    </div>
  );
}

export default AdminDashboardPage;