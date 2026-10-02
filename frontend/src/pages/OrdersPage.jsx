import { useEffect, useState } from "react";
import api from "../services/api";

function OrdersPage() {

  const [orders, setOrders] = useState([]);

  useEffect(() => {
    api.get("/orders")
      .then(res => setOrders(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div style={{ padding: "20px" }}>

      <h1>Your Orders</h1>

      {orders.length === 0 ? (
        <p>No orders yet</p>
      ) : (
        orders.map(order => (
          <div key={order.order_id}
            style={{
              border:"1px solid #ccc",
              padding:"15px",
              marginBottom:"15px"
            }}>

            <h3>Order #{order.order_id}</h3>
            <p>Total: ₪{order.total_price}</p>

            {order.items.map((item,index)=>(
              <p key={index}>
                {item.name} x {item.quantity}
              </p>
            ))}

          </div>
        ))
      )}

    </div>
  );
}

export default OrdersPage;