# Inventory Management System for Furniture Business

## Project Overview

This project is a production-ready, modular Inventory Management System built
for a furniture business dealing in almirahs, wardrobes, cabinets, and related
products. It runs locally on a desktop machine using Python and SQLite, with a
clean service-based architecture that keeps the database, business logic,
reporting, and command-line interface separated.

The application is designed for practical day-to-day business use:

- Manage furniture products with categories such as Steel Almirah and Wooden Almirah
- Track stock movement and prevent negative inventory
- Record sales and automatically update stock
- Reserve stock through preorders and track delivery status
- View dashboard summaries, low-stock alerts, and business reports

## Project Structure

```text
inventory_system/
├── main.py
├── database/
│   ├── __init__.py
│   ├── db.py
│   ├── inventory.db
│   └── models.py
├── services/
│   ├── __init__.py
│   ├── inventory_service.py
│   ├── preorder_service.py
│   └── sales_service.py
├── cli/
│   ├── __init__.py
│   └── interface.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── reports/
│   ├── __init__.py
│   └── report_generator.py
└── README.md
```

## Features

- Product CRUD operations with unique product codes
- Product search by name, code, or category
- Stock management for incoming inventory
- Sales recording with automatic stock reduction
- Preorder creation with reserved stock tracking
- Preorder status updates from pending to delivered
- Inventory dashboard with total inventory value, total sales revenue, and low-stock alerts
- Reports for sales, inventory, and preorders
- Sample data seeded automatically on first run
- User-friendly validation and error handling

## Setup Instructions

1. Ensure Python 3.10 or later is installed.
2. Open a terminal in the `inventory_system` directory.
3. Run the application:

```bash
python main.py
```

The SQLite database file is created automatically in `database/inventory.db`.

## Usage Examples

### Add a product

Use menu option `1` and enter:

- Product name: `Royal Steel Almirah`
- Product code: `ALM-S-501`
- Category: `Steel Almirah`
- Price: `21500`
- Opening quantity: `6`
- Description: `Heavy-duty steel almirah with internal locker`

### Record a sale

Use menu option `7` and enter:

- Product code: `ALM-S-101`
- Quantity sold: `2`

### Create a preorder

Use menu option `8`, then select `1`:

- Product code: `ALM-W-201`
- Customer name: `Amit Sharma`
- Reserved quantity: `1`

## Sample Data

The system automatically creates sample furniture products on first launch:

- Classic Steel Almirah
- Premium Wooden Almirah
- Sliding Door Wardrobe
- Compact Storage Cabinet

## Business Rules Implemented

- Product codes must be unique
- Price cannot be negative
- Quantity cannot be negative
- Sales cannot reduce stock below zero
- Preorders reserve stock by reducing currently available quantity
- Preorders are tracked separately and can be marked as delivered
- Low-stock warnings are shown automatically on the dashboard

## Future Enhancements

- Export reports to CSV or PDF
- Add authentication for multi-user desktop environments
- Introduce supplier purchase orders
- Add GST/tax handling and invoice printing
