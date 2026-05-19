"""Inventory service for product and stock management."""

from __future__ import annotations

import sqlite3

from database.db import get_connection
from database.models import Product


LOW_STOCK_THRESHOLD = 5


class InventoryService:
    """Provides product management and stock-related operations."""

    def add_product(
        self,
        name: str,
        code: str,
        category: str,
        price: float,
        quantity: int,
        description: str,
    ) -> Product:
        """Validate and create a new product."""
        self._validate_product_fields(name, code, category, price, quantity)
        product = Product.new(
            name=name.strip(),
            code=code.strip().upper(),
            category=category.strip(),
            price=price,
            quantity=quantity,
            description=description.strip(),
        )

        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO products (
                        name, code, category, price, quantity, description, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product.name,
                        product.code,
                        product.category,
                        product.price,
                        product.quantity,
                        product.description,
                        product.created_at,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Product code '{product.code}' already exists."
            ) from exc

        return self.get_product_by_code(product.code)

    def update_product(
        self,
        code: str,
        *,
        name: str | None = None,
        category: str | None = None,
        price: float | None = None,
        quantity: int | None = None,
        description: str | None = None,
    ) -> Product:
        """Update mutable product fields."""
        product = self.get_product_by_code(code)
        if not product:
            raise ValueError(f"Product with code '{code}' was not found.")

        new_name = name.strip() if name is not None and name.strip() else product.name
        new_category = (
            category.strip() if category is not None and category.strip()
            else product.category
        )
        new_price = product.price if price is None else price
        new_quantity = product.quantity if quantity is None else quantity
        new_description = (
            description.strip() if description is not None else product.description
        )

        self._validate_product_fields(
            new_name,
            product.code,
            new_category,
            new_price,
            new_quantity,
        )

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE products
                SET name = ?, category = ?, price = ?, quantity = ?, description = ?
                WHERE code = ?
                """,
                (
                    new_name,
                    new_category,
                    new_price,
                    new_quantity,
                    new_description,
                    product.code,
                ),
            )
            connection.commit()

        return self.get_product_by_code(product.code)

    def delete_product(self, code: str) -> None:
        """Delete a product when it has no dependent sales or preorders."""
        normalized_code = code.strip().upper()
        if not self.get_product_by_code(normalized_code):
            raise ValueError(f"Product with code '{normalized_code}' was not found.")

        try:
            with get_connection() as connection:
                connection.execute(
                    "DELETE FROM products WHERE code = ?",
                    (normalized_code,),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Cannot delete a product with recorded sales or preorders."
            ) from exc

    def list_products(self) -> list[Product]:
        """Return all products ordered by category and name."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM products
                ORDER BY category ASC, name ASC
                """
            ).fetchall()
        return [Product.from_row(row) for row in rows]

    def search_products(self, query: str) -> list[Product]:
        """Search products by name, code, or category."""
        pattern = f"%{query.strip()}%"
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM products
                WHERE name LIKE ? OR code LIKE ? OR category LIKE ?
                ORDER BY name ASC
                """,
                (pattern, pattern, pattern),
            ).fetchall()
        return [Product.from_row(row) for row in rows]

    def get_product_by_code(self, code: str) -> Product | None:
        """Fetch a product by its unique product code."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE code = ?",
                (code.strip().upper(),),
            ).fetchone()
        return Product.from_row(row) if row else None

    def add_stock(self, code: str, quantity: int) -> Product:
        """Increase stock for a product."""
        if quantity <= 0:
            raise ValueError("Stock quantity must be greater than zero.")

        product = self.get_product_by_code(code)
        if not product:
            raise ValueError(f"Product with code '{code}' was not found.")

        updated_quantity = product.quantity + quantity
        return self.update_product(code, quantity=updated_quantity)

    def reduce_stock(self, code: str, quantity: int) -> Product:
        """Reduce stock while preventing negative inventory."""
        if quantity <= 0:
            raise ValueError("Reduction quantity must be greater than zero.")

        product = self.get_product_by_code(code)
        if not product:
            raise ValueError(f"Product with code '{code}' was not found.")
        if product.quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.code}'. "
                f"Available: {product.quantity}, requested: {quantity}."
            )

        updated_quantity = product.quantity - quantity
        return self.update_product(code, quantity=updated_quantity)

    def get_inventory_value(self) -> float:
        """Return the total valuation of current inventory."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(price * quantity), 0) AS total_value FROM products"
            ).fetchone()
        return float(row["total_value"])

    def get_low_stock_products(
        self, threshold: int = LOW_STOCK_THRESHOLD
    ) -> list[Product]:
        """Return products at or below the low-stock threshold."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM products
                WHERE quantity <= ?
                ORDER BY quantity ASC, name ASC
                """,
                (threshold,),
            ).fetchall()
        return [Product.from_row(row) for row in rows]

    def summarize_inventory(self) -> dict[str, object]:
        """Return dashboard-level inventory insights."""
        products = self.list_products()
        return {
            "product_count": len(products),
            "inventory_value": self.get_inventory_value(),
            "low_stock_items": self.get_low_stock_products(),
        }

    @staticmethod
    def _validate_product_fields(
        name: str,
        code: str,
        category: str,
        price: float,
        quantity: int,
    ) -> None:
        """Validate core product fields."""
        if not name.strip():
            raise ValueError("Product name is required.")
        if not code.strip():
            raise ValueError("Product code is required.")
        if not category.strip():
            raise ValueError("Product category is required.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")
