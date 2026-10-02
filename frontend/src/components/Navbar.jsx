import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Navbar() {
  const { user, logout } = useAuth();

  const navStyle = {
    padding: "18px 24px",
    borderBottom: "1px solid #ddd",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap"
  };

  const leftStyle = {
    display: "flex",
    alignItems: "center",
    gap: "14px",
    flexWrap: "wrap"
  };

  const rightStyle = {
    display: "flex",
    alignItems: "center",
    gap: "14px",
    flexWrap: "wrap"
  };

  return (
    <nav style={navStyle}>
      <div style={leftStyle}>
        {user && user.role !== "admin" && <Link to="/home">Home</Link>}
        {user && user.role !== "admin" && <Link to="/ai-assistant">AI Assistant</Link>}
        {user && user.role !== "admin" && <Link to="/cart">Cart</Link>}
        {user && user.role !== "admin" && <Link to="/orders">Orders</Link>}

        {user && user.role === "admin" && <Link to="/admin">Admin Home</Link>}
        {user && user.role === "admin" && <Link to="/admin/add-product">Add Product</Link>}
        {user && user.role === "admin" && <Link to="/admin/ai-product">AI Product</Link>}
      </div>

      {user && (
        <div style={rightStyle}>
          <span>Hello, {user.full_name}</span>
          <button onClick={logout}>Logout</button>
        </div>
      )}
    </nav>
  );
}

export default Navbar;