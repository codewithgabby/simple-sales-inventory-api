# Saleszy API

> **A production-ready multi-tenant inventory and sales management backend built with FastAPI.**

Saleszy API is a scalable Software-as-a-Service (SaaS) backend designed to help small and medium-sized businesses manage inventory, sales, products, and business reporting from a single secure platform.

Built using modern backend engineering principles, the project demonstrates production-ready REST API development, secure authentication, relational database modeling, payment integration, and clean software architecture.

Every business operates within its own isolated workspace using a multi-tenant architecture, ensuring complete separation of customer data while sharing a single backend application.

---

## Project Overview

Saleszy was built to simulate a real-world SaaS backend that could serve thousands of businesses from one application.

The project focuses on backend engineering best practices including:

* Multi-tenant architecture
* RESTful API design
* JWT Authentication
* Role-Based Authorization
* PostgreSQL database design
* Secure payment integration
* Automated reporting
* API documentation
* Production-ready backend architecture

Rather than building a simple CRUD application, Saleszy models how a modern commercial inventory platform would be designed for scalability, maintainability, and security.

---

# Problem Solved

Many small businesses still manage inventory using notebooks or spreadsheets.

This creates several challenges:

* Lost inventory records
* Inaccurate stock levels
* Poor sales tracking
* No centralized reporting
* Security concerns
* Difficulty scaling as the business grows

Saleszy solves these problems by providing a centralized backend platform where each business securely manages its own products, inventory, sales, and reports while remaining completely isolated from every other business on the platform.

---

# Key Features

### Authentication & Security

* JWT-based Authentication
* Secure password hashing using Argon2
* Protected API endpoints
* Business-level authorization
* Password reset via email
* Rate limiting for API protection

---

### Business Management

* One business per account
* Complete tenant isolation
* Secure business ownership validation

---

### Product & Inventory Management

* Create products
* Update products
* Delete products
* Track inventory levels
* Automatic stock deduction after every sale
* Inventory availability validation

---

### Sales Management

* Record sales transactions
* Calculate revenue automatically
* View sales history
* Retrieve individual sales records

---

### Reporting & Analytics

* Daily sales reports
* Weekly sales reports
* Monthly sales reports
* Revenue summaries
* Export-ready business analytics

---

### Export System

* Free daily Excel exports
* Premium weekly exports
* Premium monthly exports
* Automatic payment verification before download

---

### Payment Integration

* Paystack Bank Transfer integration
* Secure webhook verification
* Automatic export activation after payment

---

### Developer Experience

* Interactive Swagger Documentation
* RESTful API Design
* Modular Project Structure
* Clean Architecture
* SQLAlchemy ORM
* Alembic Database Migrations

---

# System Architecture

Saleszy follows a layered backend architecture that separates business logic from database operations, making the project scalable, maintainable, and easy to extend.

```text
                Client Applications
      (Web • Mobile • Admin Dashboard)

                     │
                     ▼

             FastAPI REST API Layer

                     │
                     ▼

      Authentication & Authorization

                     │
                     ▼

            Business Service Layer

                     │
                     ▼

           Repository / Data Layer

                     │
                     ▼

              PostgreSQL Database
```

This architecture allows the application to remain modular while keeping business logic independent from the database layer.

---

# 🛠 Technology Stack

| Category            | Technology        |
| ------------------- | ----------------- |
| Language            | Python 3          |
| Framework           | FastAPI           |
| Database            | PostgreSQL        |
| ORM                 | SQLAlchemy        |
| Database Migrations | Alembic           |
| Authentication      | JWT               |
| Password Security   | Argon2            |
| API Documentation   | Swagger / OpenAPI |
| Payment Gateway     | Paystack          |
| Excel Reports       | OpenPyXL          |
| Deployment          | Railway           |
| Version Control     | Git & GitHub      |

---

# Backend Concepts Demonstrated

This project showcases practical backend engineering concepts commonly used in production systems:

* Multi-Tenant SaaS Architecture
* REST API Development
* Authentication & Authorization
* Repository Pattern
* Service Layer Architecture
* Database Relationships
* Environment Configuration
* API Security
* Payment Gateway Integration
* Reporting Systems
* File Generation
* Error Handling
* Validation
* Modular Code Organization

---

# Project Structure

The project follows a modular architecture that separates concerns, making the codebase easier to maintain and extend.

```text
simple-sales-inventory-api/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── dependencies/
│   ├── middleware/
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── alembic/
├── tests/
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

---

# Getting Started

## Clone the Repository

```bash
git clone https://github.com/codewithgabby/simple-sales-inventory-api.git

cd simple-sales-inventory-api
```

---

## Create a Virtual Environment

### Windows

```bash
python -m venv env

env\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv env

source env/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=your_secret_key

DATABASE_URL=postgresql://username:password@localhost:5432/saleszy_db

PAYSTACK_SECRET_KEY=your_paystack_secret

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

EMAIL_FROM=Saleszy <your_email@gmail.com>

FRONTEND_RESET_URL=http://localhost:3000/reset-password
```

---

## Run Database Migrations

```bash
alembic upgrade head
```

---

## Start the Development Server

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```
http://127.0.0.1:8000
```

---

# API Documentation

FastAPI automatically generates interactive API documentation.

Once the server is running, visit:

### Swagger UI

```
http://127.0.0.1:8000/docs
```

### ReDoc

```
http://127.0.0.1:8000/redoc
```

These interfaces allow developers to explore, test, and understand every API endpoint without additional tools.

---

# Testing

Run the test suite using:

```bash
pytest
```

Future versions of the project will include:

* Unit Tests
* Integration Tests
* API Tests
* GitHub Actions CI Pipeline

---

# Deployment

Saleszy is designed to be deployable on modern cloud platforms such as:

* Railway
* Render
* Docker
* DigitalOcean
* AWS
* Azure

Deployment configuration is currently being expanded as the project evolves.

---

# API Endpoint Overview

| Module         | Description                                                  |
| -------------- | ------------------------------------------------------------ |
| Authentication | User registration, login, password reset, JWT authentication |
| Business       | Business profile and tenant management                       |
| Products       | Product CRUD operations                                      |
| Inventory      | Inventory management and stock updates                       |
| Sales          | Sales recording and history                                  |
| Reports        | Daily, weekly, and monthly reports                           |
| Exports        | Excel report generation                                      |
| Payments       | Paystack webhook verification                                |

---

# Roadmap

The following features are planned for future releases:

## Version 2.0

* Multi-user businesses
* Employee roles and permissions
* Customer management
* Supplier management
* Purchase Orders
* Barcode support
* Invoice generation
* Receipt printing
* Notifications
* Activity logs

---

## Version 3.0

* Docker deployment
* Redis caching
* Background jobs using Celery
* Email notifications
* Business analytics dashboard
* Mobile API optimization
* WebSocket live inventory updates
* Public Developer API
* CI/CD with GitHub Actions
* Comprehensive test coverage

---

# Contributing

Contributions are welcome.

If you'd like to improve Saleszy API:

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push your branch.
5. Open a Pull Request.

Suggestions, bug reports, and feature requests are always appreciated.

---

# License

This project is licensed under the MIT License.

Feel free to use this project for learning and educational purposes.

---

# Author

## Johnson Gabriel Ohimai

Python Backend Engineer

Passionate about building scalable backend systems, SaaS platforms, and AI-powered software.

### Connect with me

* Portfolio: https://gabbydev.netlify.app
* LinkedIn: https://www.linkedin.com/in/johnson-gabriel-b716aa212/
* GitHub: https://github.com/codewithgabby
* Email: [j.gabriel.dev77@gmail.com](mailto:j.gabriel.dev77@gmail.com)

---

# Support the Project

If you found this project useful or interesting:

Star this repository

Fork the project

Share feedback or suggestions

Every star helps increase the visibility of the project.

---

> **Built with LOVE using Python, FastAPI, PostgreSQL, and modern backend engineering practices.**



