# SmartStore

SmartStore is a full-stack e-commerce web application with a Flask API backend and a React/Vite frontend. It supports user authentication, product browsing and search, cart management, checkout, order history, admin product management, and AI-assisted product search/recommendations.

## Features

- User registration, login, and JWT-protected sessions
- Product catalog browsing and keyword search
- Shopping cart with quantity updates and stock validation
- Checkout flow that creates orders and reduces product stock
- Order history for signed-in users
- Role-based admin area
- Admin product create, edit, delete, and search
- AI assistant for user product recommendations
- AI-assisted admin product drafting and listing improvement
- OpenAI-backed AI behavior with fallback logic when AI is unavailable

## Tech Stack

### Backend

- Python
- Flask
- Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-CORS
- Flask-Limiter
- MySQL through PyMySQL
- OpenAI Python SDK

### Frontend

- React
- Vite
- React Router
- Axios

## Project Structure

```text
smartstore/
|-- backend/
|   |-- app.py
|   |-- config.py
|   |-- extensions.py
|   |-- requirements.txt
|   |-- models/
|   |-- routes/
|   `-- services/
|-- frontend/
|   |-- index.html
|   |-- package.json
|   |-- vite.config.js
|   |-- public/
|   `-- src/
`-- ReadMe.md
```

## Prerequisites

- Python 3.10+
- Node.js and npm
- MySQL server
- An OpenAI API key if you want AI responses from OpenAI

The app still works in limited fallback mode without an OpenAI key for some AI-related features, but admin AI drafting requires OpenAI configuration to be useful.

## Backend Setup

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SECRET_KEY=replace-with-a-secret-key
JWT_SECRET_KEY=replace-with-a-jwt-secret-key

DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=smartstore

AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini

FLASK_DEBUG=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
RATELIMIT_STORAGE_URI=memory://
```

Create the database in MySQL:

```sql
CREATE DATABASE smartstore;
```

This project does not currently include migrations or a seed script. To create the database tables from the SQLAlchemy models, run:

```powershell
cd backend
python
```

Then in the Python shell:

```python
from app import app
from extensions import db

with app.app_context():
    db.create_all()
```

Start the backend:

```powershell
python app.py
```

By default, Flask runs at:

```text
http://127.0.0.1:5000
```

## Frontend Setup

From the project root:

```powershell
cd frontend
npm install
```

Create or update `frontend/.env.development`:

```env
VITE_API_URL=http://127.0.0.1:5000
```

Start the frontend:

```powershell
npm run dev
```

Vite will print the local development URL, usually:

```text
http://localhost:5173
```

## User Roles

Newly registered users are created with the `user` role. Admin-only pages and endpoints require a user record with:

```text
role = admin
```

There is no admin creation screen in the current app, so admin users must be promoted directly in the database.

Example:

```sql
UPDATE users
SET role = 'admin'
WHERE email = 'admin@example.com';
```

## Frontend Routes

- `/login` - user login
- `/register` - user registration
- `/home` - product catalog and search
- `/ai-assistant` - AI shopping assistant for normal users
- `/cart` - current user's cart
- `/orders` - current user's order history
- `/admin` - admin product dashboard
- `/admin/add-product` - manually add a product
- `/admin/ai-product` - create a product draft with AI assistance
- `/admin/products/:id/edit` - edit an existing product

## API Overview

### Auth

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Log in and receive a JWT |
| GET | `/auth/me` | Get the current authenticated user |

### Products

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/products` | List all products |
| GET | `/products/search?query=...` | Search products by keyword |

### Cart

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/cart` | Get the current user's cart |
| POST | `/cart/add` | Add a product to the cart |
| PUT | `/cart/update` | Update a cart item quantity |
| DELETE | `/cart/remove/<cart_item_id>` | Remove an item from the cart |

### Orders

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/orders/checkout` | Create an order from the cart |
| GET | `/orders` | List the current user's orders |

### AI

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/ai/search` | Interpret a product search query and return matching products |
| POST | `/ai/chat` | Chat with the product assistant |

Both AI endpoints require a signed-in user and have per-user rate and input limits.

### Admin

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/admin/products` | Create a product |
| GET | `/admin/products/<product_id>` | Get a product for editing |
| PATCH | `/admin/products/<product_id>` | Update a product |
| DELETE | `/admin/products/<product_id>` | Delete a product |
| POST | `/admin/products/<product_id>/ai-improve` | Improve an existing listing with AI |
| POST | `/admin/ai-product/interpret` | Build or refine a product draft with AI |

Admin AI endpoints are rate-limited to 3 requests per day per admin user. Products referenced by past orders cannot be deleted; the API returns HTTP 409 to preserve order history.

## Production Notes

- Set `FLASK_DEBUG=false` and `CORS_ORIGINS=https://smartstore-project.click` on the backend.
- Set `RATELIMIT_STORAGE_URI` to a persistent Redis URL in production. The default in-memory limiter is for local development only. Configure an OpenAI project budget as a further cost cap.
- On a Linux host, serve `app:app` from `backend/` with `gunicorn --bind 127.0.0.1:5000 app:app`, behind a TLS reverse proxy on port 443. Keep the Flask development server private.
- Provide the backend secrets and MySQL settings through the host environment or an untracked `backend/.env`. Build the frontend with `VITE_API_URL` pointing to the HTTPS API origin.
- Verify DNS, EC2 instance health, security group/firewall access to port 443, reverse proxy health, and the backend service independently. These resources are not configured by this repository.

Run the focused backend tests with `cd backend; python -B -m unittest discover -s tests -v`. Run `npm run lint` and `npm run build` from `frontend/`.

## Data Model

- `users`: account information, password hash, role, and creation date
- `products`: catalog item details, category, tags, price, and stock
- `cart_items`: user cart entries with product and quantity
- `orders`: order header with user, total price, status, and creation date
- `order_items`: individual order line items with product, quantity, and unit price

## Common Development Commands

Backend:

```powershell
cd backend
python app.py
```

Frontend:

```powershell
cd frontend
npm run dev
npm run build
npm run lint
```

## Notes and Current Limitations

- The project does not currently include Flask migrations.
- The project does not currently include automated tests.
- The project does not include product seed data.
- Admin users must be assigned manually in the database.
- The frontend depends on `VITE_API_URL`; requests will fail if it is missing or points to the wrong backend URL.
- The backend depends on MySQL environment variables in `backend/.env`.
