# Simple Sales & Inventory API

A multi-tenant SaaS backend built with **FastAPI** for small vendors to track:
- Products
- Inventory
- Sales
- Revenue reports
- Paid export statements

Each business is fully isolated using `business_id`.

---

## Features

- JWT authentication
- One business per user (v1)
- Product & inventory management
- Sales recording with stock deduction
- Daily, weekly, monthly sales reports
- Excel exports (daily free, weekly/monthly paid)
- Paystack bank-transfer webhook integration
- Rate limiting & password hardening

---

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT (python-jose)
- Argon2 password hashing
- Paystack Webhooks
- OpenPyXL (Excel exports)

---

## Authentication

- `POST /auth/signup`
- `POST /auth/login`

JWT tokens are required for all protected endpoints.

---

## Core Endpoints

### Products
- `POST /products`
- `GET /products`
- `PUT /products/{id}`
- `DELETE /products/{id}`

### Inventory
- `POST /inventory/{product_id}`
- `PUT /inventory/{product_id}`
- `GET /inventory`

### Sales
- `POST /sales`
- `GET /sales`
- `GET /sales/{sale_id}`

### Reports
- `GET /reports/daily`
- `GET /reports/weekly`
- `GET /reports/monthly`

### Exports
- `GET /exports/daily` (free)
- `GET /exports/weekly` (paid)
- `GET /exports/monthly` (paid)

---

## Payments

- Weekly and monthly exports require payment
- Vendors pay via **Paystack bank transfer**
- Paystack notifies the backend via webhook
- Export access is unlocked automatically

Webhook endpoint:

---

## Environment Variables

Create a `.env` file with:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
PAYSTACK_SECRET_KEY=sk_test_or_live_key

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
EMAIL_FROM=Your App <email>

FRONTEND_RESET_URL=https://your-frontend/reset-password

python -m venv env
source env/bin/activate  # or env\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

### Notes

This project is designed as a single backend, multi-tenant SaaS

All data is scoped by business_id

No frontend included in this repository

