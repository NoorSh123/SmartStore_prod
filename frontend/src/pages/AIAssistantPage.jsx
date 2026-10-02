import { useEffect, useRef, useState } from "react";
import api from "../services/api";

const openingMessage = {
  role: "assistant",
  content: "Hi! Tell me what you are looking for, and I will recommend products from SmartStore."
};

function AIAssistantPage() {
  const [message, setMessage] = useState("");
  const [chatMessages, setChatMessages] = useState([openingMessage]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSessionWarning, setShowSessionWarning] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const [sessionEnded, setSessionEnded] = useState(false);
  const warningTimeoutRef = useRef(null);
  const countdownIntervalRef = useRef(null);
  const sessionEndedRef = useRef(false);

  const clearSessionTimers = () => {
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
      warningTimeoutRef.current = null;
    }

    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
  };

  const startSessionTimers = () => {
    clearSessionTimers();
    setShowSessionWarning(false);
    setCountdown(30);

    warningTimeoutRef.current = setTimeout(() => {
      setShowSessionWarning(true);
      setCountdown(30);

      countdownIntervalRef.current = setInterval(() => {
        setCountdown((currentCountdown) => {
          if (currentCountdown <= 1) {
            if (sessionEndedRef.current) {
              return 0;
            }

            sessionEndedRef.current = true;
            clearSessionTimers();
            setSessionEnded(true);
            setShowSessionWarning(false);
            setChatMessages((currentMessages) => [
              ...currentMessages,
              {
                role: "assistant",
                content: "This AI session has ended. Clear the chat to start a new session."
              }
            ]);
            return 0;
          }

          return currentCountdown - 1;
        });
      }, 1000);
    }, 30000);
  };

  useEffect(() => {
    startSessionTimers();

    return () => {
      clearSessionTimers();
    };
  }, []);

  const handleSendMessage = async () => {
    if (sessionEnded) {
      setError("This AI session has ended. Clear the chat to start a new session.");
      return;
    }

    const cleanedMessage = message.trim();

    if (!cleanedMessage) {
      setError("Please type a message.");
      return;
    }

    const nextMessages = [
      ...chatMessages,
      {
        role: "user",
        content: cleanedMessage
      }
    ];

    try {
      startSessionTimers();
      setLoading(true);
      setError("");
      setMessage("");
      setChatMessages(nextMessages);

      const response = await api.post("/ai/chat", {
        messages: nextMessages.slice(-10)
      });

      setProducts(response.data.products || []);
      setChatMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: response.data.reply || "I could not find a catalog answer for that."
        }
      ]);
    } catch (err) {
      setError(err.response?.data?.error || "AI chat failed");
      setChatMessages(chatMessages);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey && !sessionEnded) {
      event.preventDefault();
      handleSendMessage();
    }
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

  const handleClear = () => {
    setMessage("");
    setChatMessages([openingMessage]);
    setProducts([]);
    setError("");
    sessionEndedRef.current = false;
    setSessionEnded(false);
    startSessionTimers();
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>AI Assistant</h1>

      <p>
        Chat with the assistant about products currently available in SmartStore.
      </p>

      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "15px",
          maxWidth: "800px",
          minHeight: "220px",
          marginBottom: "15px",
          background: "#fafafa"
        }}
      >
        {chatMessages.map((item, index) => (
          <div
            key={`${item.role}-${index}`}
            style={{
              display: "flex",
              justifyContent: item.role === "user" ? "flex-end" : "flex-start",
              marginBottom: "10px"
            }}
          >
            <div
              style={{
                maxWidth: "75%",
                padding: "10px 12px",
                borderRadius: "8px",
                background: item.role === "user" ? "#dceeff" : "#ffffff",
                border: "1px solid #ddd"
              }}
            >
              <strong>{item.role === "user" ? "You" : "AI"}:</strong>{" "}
              {item.content}
            </div>
          </div>
        ))}

        {showSessionWarning && !sessionEnded && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-start",
              marginBottom: "10px"
            }}
          >
            <div
              style={{
                maxWidth: "75%",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "#ffffff",
                border: "1px solid #ddd"
              }}
            >
              <strong>AI:</strong> Do you have any more questions?
              <br />
              This session will end in {countdown} seconds.
            </div>
          </div>
        )}
      </div>

      <div style={{ marginBottom: "15px" }}>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sessionEnded}
          placeholder="Example: I want a comfortable mouse for long hours of computer work"
          rows="3"
          style={{
            width: "100%",
            maxWidth: "800px",
            padding: "12px",
            borderRadius: "8px",
            border: "1px solid #ccc"
          }}
        />
      </div>

      <div style={{ marginBottom: "20px" }}>
        <button
          onClick={handleSendMessage}
          disabled={loading || sessionEnded}
          style={{ marginRight: "10px" }}
        >
          {loading ? "Thinking..." : "Send"}
        </button>

        <button onClick={handleClear} disabled={loading}>
          Clear
        </button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2>Recommended Products</h2>

      {products.length === 0 ? (
        <p>No recommendations yet.</p>
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

            <p>
              <strong>Category:</strong> {product.category}
            </p>

            <p>
              <strong>Tags:</strong> {product.tags}
            </p>

            <p>
              <strong>Price:</strong> ILS {product.price}
            </p>

            <p>
              <strong>Stock:</strong> {product.stock}
            </p>

            <button onClick={() => handleAddToCart(product.id)}>
              Add to Cart
            </button>
          </div>
        ))
      )}
    </div>
  );
}

export default AIAssistantPage;
