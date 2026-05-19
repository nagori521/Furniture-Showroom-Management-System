# Furniture Showroom Management System

## Overview

This project is a production-ready showroom management system for a furniture
business focused on almirahs, wardrobes, cabinets, and related products. It is
built with Flask, SQLite, Bootstrap, a clean service layer, and PDF invoice
generation through ReportLab.

The system supports:

- admin login
- product and stock management
- customer management
- sales with invoice generation
- preorder reservation with delivery tracking
- management dashboard and reports

## Project Structure

```text
inventory_app/
├── app.py
├── config.py
├── database/
│   ├── db.py
│   ├── inventory.db
│   └── models.py
├── routes/
│   ├── auth_routes.py
│   ├── customer_routes.py
│   ├── dashboard_routes.py
│   ├── preorder_routes.py
│   ├── product_routes.py
│   ├── report_routes.py
│   └── sales_routes.py
├── services/
│   ├── auth_service.py
│   ├── customer_service.py
│   ├── inventory_service.py
│   ├── preorder_service.py
│   ├── report_service.py
│   └── sales_service.py
├── templates/
│   ├── add_product.html
│   ├── base.html
│   ├── customers.html
│   ├── dashboard.html
│   ├── edit_customer.html
│   ├── edit_product.html
│   ├── invoice.html
│   ├── login.html
│   ├── preorders.html
│   ├── products.html
│   ├── reports.html
│   └── sales.html
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
└── utils/
    └── auth.py
```

## Main Features

- Admin authentication with protected routes
- Product CRUD with category support and stock updates
- Low-stock warnings on the dashboard
- Customer master records for sales and preorders
- Sales with customer selection, stock reduction, and invoice numbers
- HTML invoice view and downloadable PDF invoice
- Preorders with delivery date and status tracking
- Upcoming delivery panel on dashboard and preorder page
- Reports for sales, inventory, and delivery schedules
- Sample data for products and customers

## Setup

Install dependencies:

```bash
pip install flask sqlalchemy reportlab
```

Run the app:

```bash
cd inventory_app
python app.py
```

Open in browser:

```text
http://127.0.0.1:5000
```

## Default Admin

- Username: `admin`
- Password: `admin123`

## Sample Data

Seeded automatically on first run:

- furniture products
- sample customers
- a default walk-in customer for migrated records

## Reports Included

- Sales report with date filter
- Inventory report
- Preorder delivery report

## Notes

- The database is stored at `inventory_app/database/inventory.db`.
- SQLAlchemy is included in the install command for future extensibility, while
  the current implementation uses a lightweight SQLite service layer.
- Existing legacy sales and preorder tables are migrated automatically to the
  new schema when possible.

## Future Extensions

- REST API for website or mobile integration
- role-based permissions
- GST/tax support and print-friendly billing
- supplier and purchase-order modules
