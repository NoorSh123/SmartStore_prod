import { useState } from "react";
import api from "../services/api";

function AdminAddProductPage() {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    bullet_points: "",
    category: "",
    tags: "",
    price: "",
    stock: ""
  });

  const [creatingProduct, setCreatingProduct] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    try {
      setCreatingProduct(true);

      await api.post("/admin/products", {
        name: formData.name,
        description: formData.description,
        bullet_points: formData.bullet_points,
        category: formData.category,
        tags: formData.tags,
        price: formData.price,
        stock: formData.stock
      });

      setSuccess("Product created successfully.");

      setFormData({
        name: "",
        description: "",
        bullet_points: "",
        category: "",
        tags: "",
        price: "",
        stock: ""
      });
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create product");
    } finally {
      setCreatingProduct(false);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Add Product</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {success && <p style={{ color: "green" }}>{success}</p>}

      <form onSubmit={handleCreateProduct}>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="text"
            name="name"
            placeholder="Product Name"
            value={formData.name}
            onChange={handleChange}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <textarea
            name="description"
            placeholder="Description"
            value={formData.description}
            onChange={handleChange}
            rows="3"
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <textarea
            name="bullet_points"
            placeholder="Bullet points (comma separated)"
            value={formData.bullet_points}
            onChange={handleChange}
            rows="3"
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <input
            type="text"
            name="category"
            placeholder="Category"
            value={formData.category}
            onChange={handleChange}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <input
            type="text"
            name="tags"
            placeholder="Tags (comma separated)"
            value={formData.tags}
            onChange={handleChange}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <input
            type="number"
            step="0.01"
            name="price"
            placeholder="Price"
            value={formData.price}
            onChange={handleChange}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "15px" }}>
          <input
            type="number"
            name="stock"
            placeholder="Stock"
            value={formData.stock}
            onChange={handleChange}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <button type="submit" disabled={creatingProduct}>
          {creatingProduct ? "Creating..." : "Add Product"}
        </button>
      </form>
    </div>
  );
}

export default AdminAddProductPage;