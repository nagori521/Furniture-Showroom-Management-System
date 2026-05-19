"""Shared helpers for input validation, formatting, and sample data."""

from __future__ import annotations

from datetime import datetime

from services.inventory_service import InventoryService


def get_int_input(prompt: str) -> int:
    """Prompt the user until a valid integer is entered."""
    while True:
        value = input(prompt).strip()
        try:
            return int(value)
        except ValueError:
            print_error("Please enter a valid integer.")


def get_float_input(prompt: str) -> float:
    """Prompt the user until a valid float is entered."""
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print_error("Please enter a valid numeric value.")


def format_currency(amount: float) -> str:
    """Format a numeric amount as local currency style."""
    return f"Rs. {amount:,.2f}"


def format_datetime(value: str) -> str:
    """Convert an ISO timestamp into a readable display value."""
    try:
        dt_value = datetime.fromisoformat(value)
        return dt_value.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def print_section(title: str) -> None:
    """Display a section heading."""
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def print_success(message: str) -> None:
    """Display a success message."""
    print(f"[SUCCESS] {message}")


def print_error(message: str) -> None:
    """Display an error message."""
    print(f"[ERROR] {message}")


def print_info(message: str) -> None:
    """Display an informational message."""
    print(f"[INFO] {message}")


def seed_sample_data() -> None:
    """Insert sample catalog items when the product table is empty."""
    inventory_service = InventoryService()
    if inventory_service.list_products():
        return

    sample_products = [
        {
            "name": "Classic Steel Almirah",
            "code": "ALM-S-101",
            "category": "Steel Almirah",
            "price": 18500.00,
            "quantity": 8,
            "description": "Two-door powder-coated steel almirah with locker.",
        },
        {
            "name": "Premium Wooden Almirah",
            "code": "ALM-W-201",
            "category": "Wooden Almirah",
            "price": 32999.00,
            "quantity": 4,
            "description": "Solid engineered wood almirah with mirror finish.",
        },
        {
            "name": "Sliding Door Wardrobe",
            "code": "WRD-S-301",
            "category": "Wardrobe",
            "price": 41250.00,
            "quantity": 3,
            "description": "Three-panel wardrobe with sliding doors and shelves.",
        },
        {
            "name": "Compact Storage Cabinet",
            "code": "CAB-M-401",
            "category": "Storage Cabinet",
            "price": 12499.00,
            "quantity": 10,
            "description": "Multi-purpose cabinet for small room storage.",
        },
    ]

    for product in sample_products:
        inventory_service.add_product(**product)
