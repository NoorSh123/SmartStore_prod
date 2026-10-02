import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../services/api";

function AdminEditProductPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    bullet_points: "",
    category: "",
    tags: "",
    price: "",
    stock: ""
  });

  const [originalData, setOriginalData] = useState({
    name: "",
    description: "",
    bullet_points: "",
    category: "",
    tags: "",
    price: "",
    stock: ""
  });

  const [mode, setMode] = useState("view");
  const [loadingProduct, setLoadingProduct] = useState(true);
  const [savingProduct, setSavingProduct] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const mapApiProductToForm = (product) => {
    return {
      name: product?.name || "",
      description: product?.description || "",
      bullet_points: product?.bullet_points || "",
      category: product?.category || "",
      tags: product?.tags || "",
      price: product?.price ?? "",
      stock: product?.stock ?? ""
    };
  };

  const loadProduct = async () => {
    try {
      setLoadingProduct(true);
      setError("");
      setSuccess("");

      const response = await api.get(`/admin/products/${id}`);
      const mapped = mapApiProductToForm(response.data);

      setFormData(mapped);
      setOriginalData(mapped);
      setMode("view");
    } catch (err) {
      setError(err.response?.data?.error || "Failed to load product");
    } finally {
      setLoadingProduct(false);
    }
  };

  useEffect(() => {
    loadProduct();
  }, [id]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleStartManualEdit = () => {
    setError("");
    setSuccess("");
    setFormData(originalData);
    setMode("edit");
  };

  const handleAIEdit = async () => {
    try {
      setAiLoading(true);
      setError("");
      setSuccess("");

      const response = await api.post(`/admin/products/${id}/ai-improve`);
      const suggested = mapApiProductToForm(response.data.product || {});

      setFormData(suggested);
      setMode("ai_review");
    } catch (err) {
      setError(err.response?.data?.error || "AI edit failed");
    } finally {
      setAiLoading(false);
    }
  };

  const handleAcceptSuggestion = async () => {
    try {
      setSavingProduct(true);
      setError("");
      setSuccess("");

      const response = await api.patch(`/admin/products/${id}`, formData);
      const saved = mapApiProductToForm(response.data.product || formData);

      setFormData(saved);
      setOriginalData(saved);
      setMode("view");
      setSuccess("AI suggestion accepted and product updated successfully.");
    } catch (err) {
      setError(err.response?.data?.error || "Failed to accept AI suggestion");
    } finally {
      setSavingProduct(false);
    }
  };

  const handleEditSuggestion = () => {
    setError("");
    setSuccess("");
    setMode("edit");
  };

  const handleRejectSuggestion = () => {
    setError("");
    setSuccess("");
    setFormData(originalData);
    setMode("view");
  };

  const handleCancel = () => {
    setError("");
    setSuccess("");
    setFormData(originalData);
    setMode("view");
  };

  const handleSaveChanges = async (e) => {
    e.preventDefault();

    try {
      setSavingProduct(true);
      setError("");
      setSuccess("");

      const response = await api.patch(`/admin/products/${id}`, formData);
      const saved = mapApiProductToForm(response.data.product || formData);

      setFormData(saved);
      setOriginalData(saved);
      setMode("view");
      setSuccess("Product updated successfully.");
    } catch (err) {
      setError(err.response?.data?.error || "Failed to update product");
    } finally {
      setSavingProduct(false);
    }
  };

  const fieldsDisabled = mode === "view" || mode === "ai_review";

  if (loadingProduct) {
    return (
      <div style={{ padding: "20px" }}>
        <p>Loading product...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>Edit Product</h1>
      <p>Review the product first. Then choose manual edit or AI edit.</p>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {success && <p style={{ color: "green" }}>{success}</p>}

      <form onSubmit={handleSaveChanges}>
        <div style={{ marginBottom: "10px" }}>
          <input
            type="text"
            name="name"
            placeholder="Product Name"
            value={formData.name}
            onChange={handleChange}
            disabled={fieldsDisabled}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        <div style={{ marginBottom: "10px" }}>
          <textarea
            name="description"
            placeholder="Description"
            value={formData.description}
            onChange={handleChange}
            rows="4"
            disabled={fieldsDisabled}
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
            disabled={fieldsDisabled}
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
            disabled={fieldsDisabled}
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
            disabled={fieldsDisabled}
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
            disabled={fieldsDisabled}
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
            disabled={fieldsDisabled}
            style={{ width: "100%", padding: "10px" }}
          />
        </div>

        {mode === "view" && (
          <div>
            <button
              type="button"
              onClick={handleStartManualEdit}
              disabled={savingProduct || aiLoading}
              style={{ marginRight: "10px" }}
            >
              Edit
            </button>

            <button
              type="button"
              onClick={handleAIEdit}
              disabled={savingProduct || aiLoading}
              style={{ marginRight: "10px" }}
            >
              {aiLoading ? "AI Editing..." : "AI Edit"}
            </button>

            <button
              type="button"
              onClick={() => navigate("/admin")}
              disabled={savingProduct || aiLoading}
            >
              Back
            </button>
          </div>
        )}

        {mode === "edit" && (
          <div>
            <button
              type="submit"
              disabled={savingProduct || aiLoading}
              style={{ marginRight: "10px" }}
            >
              {savingProduct ? "Saving..." : "Save Changes"}
            </button>

            <button
              type="button"
              onClick={handleCancel}
              disabled={savingProduct || aiLoading}
            >
              Cancel
            </button>
          </div>
        )}

        {mode === "ai_review" && (
          <div>
            <button
              type="button"
              onClick={handleAcceptSuggestion}
              disabled={savingProduct || aiLoading}
              style={{ marginRight: "10px" }}
            >
              {savingProduct ? "Accepting..." : "Accept Suggestion"}
            </button>

            <button
              type="button"
              onClick={handleEditSuggestion}
              disabled={savingProduct || aiLoading}
              style={{ marginRight: "10px" }}
            >
              Edit Suggestion
            </button>

            <button
              type="button"
              onClick={handleRejectSuggestion}
              disabled={savingProduct || aiLoading}
            >
              Reject Suggestion
            </button>
          </div>
        )}
      </form>
    </div>
  );
}

export default AdminEditProductPage;