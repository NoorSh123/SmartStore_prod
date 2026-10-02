import { useState } from "react";
import api from "../services/api";

function AdminAIProductPage() {
  const [message, setMessage] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [draft, setDraft] = useState({
    name: "",
    description: "",
    bullet_points: "",
    category: "",
    tags: "",
    price: "",
    stock: ""
  });
  const [readyToCreate, setReadyToCreate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creatingProduct, setCreatingProduct] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const mapApiProductToForm = (product) => {
    return {
      name: product?.name || "",
      description: product?.description || "",
      bullet_points: Array.isArray(product?.bullet_points)
        ? product.bullet_points.join(", ")
        : "",
      category: product?.category || "",
      tags: Array.isArray(product?.tags)
        ? product.tags.join(", ")
        : "",
      price: product?.price ?? "",
      stock: product?.stock ?? ""
    };
  };

  const mapFormToApiDraft = () => {
    return {
      name: draft.name || null,
      description: draft.description || null,
      bullet_points: draft.bullet_points
        ? draft.bullet_points.split(",").map((item) => item.trim()).filter(Boolean)
        : [],
      category: draft.category || null,
      tags: draft.tags
        ? draft.tags.split(",").map((item) => item.trim()).filter(Boolean)
        : [],
      price: draft.price === "" ? null : Number(draft.price),
      stock: draft.stock === "" ? null : Number(draft.stock)
    };
  };

  const handleSendToAI = async () => {
    const cleanedMessage = message.trim();

    if (!cleanedMessage) {
      setError("Please describe the product or answer the AI follow-up question.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");

      const response = await api.post("/admin/ai-product/interpret", {
        message: cleanedMessage,
        current_draft: mapFormToApiDraft()
      });

      const result = response.data;

      const updatedMessages = [
        ...chatMessages,
        { role: "admin", text: cleanedMessage }
      ];

      if (result.status === "needs_clarification") {
        updatedMessages.push({
          role: "ai",
          text: result.follow_up_question || "I need more information."
        });
        setReadyToCreate(false);
      } else {
        updatedMessages.push({
          role: "ai",
          text: "I have enough information. Review the generated product below and create it."
        });
        setReadyToCreate(true);
      }

      setChatMessages(updatedMessages);
      setDraft(mapApiProductToForm(result.product || {}));
      setMessage("");
    } catch (err) {
      setError(err.response?.data?.error || "AI product generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDraftChange = (e) => {
    setDraft({
      ...draft,
      [e.target.name]: e.target.value
    });
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();

    try {
      setCreatingProduct(true);
      setError("");
      setSuccess("");

      await api.post("/admin/products", {
        name: draft.name,
        description: draft.description,
        bullet_points: draft.bullet_points,
        category: draft.category,
        tags: draft.tags,
        price: draft.price,
        stock: draft.stock
      });

      setSuccess("Product created successfully.");

      setDraft({
        name: "",
        description: "",
        bullet_points: "",
        category: "",
        tags: "",
        price: "",
        stock: ""
      });

      setChatMessages([]);
      setMessage("");
      setReadyToCreate(false);
    } catch (err) {
      setError(err.response?.data?.error || "Failed to create product");
    } finally {
      setCreatingProduct(false);
    }
  };

  const handleClear = () => {
    setMessage("");
    setChatMessages([]);
    setDraft({
      name: "",
      description: "",
      bullet_points: "",
      category: "",
      tags: "",
      price: "",
      stock: ""
    });
    setReadyToCreate(false);
    setError("");
    setSuccess("");
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Admin AI Product Page</h1>
      <p>
        Describe the product in natural language. The AI will build a product draft
        and ask follow-up questions if required information is missing.
      </p>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {success && <p style={{ color: "green" }}>{success}</p>}

      <div
        style={{
          border: "1px solid #ccc",
          padding: "15px",
          marginBottom: "20px",
          borderRadius: "8px"
        }}
      >
        <h2>AI Conversation</h2>

        {chatMessages.length === 0 ? (
          <p>No conversation yet.</p>
        ) : (
          chatMessages.map((item, index) => (
            <div
              key={index}
              style={{
                marginBottom: "10px",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "8px"
              }}
            >
              <strong>{item.role === "admin" ? "Admin" : "AI"}:</strong> {item.text}
            </div>
          ))
        )}

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Example: I have 150 BMW cars for purchasing. It can do highway driving, has leather seats, GPS, and advanced safety features."
          rows="5"
          style={{
            width: "100%",
            padding: "10px",
            marginTop: "10px",
            marginBottom: "10px",
            boxSizing: "border-box"
          }}
        />

        <button onClick={handleSendToAI} disabled={loading} style={{ marginRight: "10px" }}>
          {loading ? "Processing..." : "Send to AI"}
        </button>

        <button onClick={handleClear} disabled={loading || creatingProduct}>
          Clear
        </button>
      </div>

      <div
        style={{
          border: "1px solid #ccc",
          padding: "15px",
          borderRadius: "8px"
        }}
      >
        <h2>Generated Product Draft</h2>

        <form onSubmit={handleCreateProduct}>
          <div style={{ marginBottom: "10px" }}>
            <input
              type="text"
              name="name"
              placeholder="Product Name"
              value={draft.name}
              onChange={handleDraftChange}
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "10px" }}>
            <textarea
              name="description"
              placeholder="Description"
              value={draft.description}
              onChange={handleDraftChange}
              rows="3"
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "10px" }}>
            <textarea
              name="bullet_points"
              placeholder="Bullet points (comma separated)"
              value={draft.bullet_points}
              onChange={handleDraftChange}
              rows="3"
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "10px" }}>
            <input
              type="text"
              name="category"
              placeholder="Category"
              value={draft.category}
              onChange={handleDraftChange}
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "10px" }}>
            <input
              type="text"
              name="tags"
              placeholder="Tags (comma separated)"
              value={draft.tags}
              onChange={handleDraftChange}
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "10px" }}>
            <input
              type="number"
              step="0.01"
              name="price"
              placeholder="Price"
              value={draft.price}
              onChange={handleDraftChange}
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <div style={{ marginBottom: "15px" }}>
            <input
              type="number"
              name="stock"
              placeholder="Stock"
              value={draft.stock}
              onChange={handleDraftChange}
              style={{ width: "100%", padding: "10px" }}
            />
          </div>

          <button type="submit" disabled={!readyToCreate || creatingProduct}>
            {creatingProduct ? "Creating..." : "Create Product"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AdminAIProductPage;