"""Inventory service responsible for product and stock workflows."""

from __future__ import annotations

import sqlite3

from config import Config
from database.db import get_connection
from database.models import Product, utc_now_iso


class InventoryService:
    """Encapsulates product CRUD and stock operations."""

    def add_product(
        self,
        name: str,
        code: str,
        category: str,
        price: float,
        quantity: int,
        description: str,
    ) -> Product:
        """Create a validated product record."""
        normalized_code = code.strip().upper()
        self._validate_product_fields(name, normalized_code, category, price, quantity)

        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO products (
                        name, code, category, price, quantity, description, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name.strip(),
                        normalized_code,
                        category.strip(),
                        price,
                        quantity,
                        description.strip(),
                        utc_now_iso(),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Product code '{normalized_code}' already exists."
            ) from exc

        return self.get_product_by_id(cursor.lastrowid)

    def update_product(
        self,
        product_id: int,
        name: str,
        category: str,
        price: float,
        quantity: int,
        description: str,
    ) -> Product:
        """Update editable fields for an existing product."""
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")

        self._validate_product_fields(
            name,
            product.code,
            category,
            price,
            quantity,
        )

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE products
                SET name = ?, category = ?, price = ?, quantity = ?, description = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    category.strip(),
                    price,
                    quantity,
                    description.strip(),
                    product_id,
                ),
            )
            connection.commit()

        return self.get_product_by_id(product_id)

    def delete_product(self, product_id: int) -> None:
        """Delete a product when it has no linked sales or preorders."""
        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")

        try:
            with get_connection() as connection:
                connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Cannot delete a product with existing sales or preorders."
            ) from exc

    def get_product_by_id(self, product_id: int) -> Product | None:
        """Return a product by primary key."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
        return Product.from_row(row) if row else None

    def get_product_by_code(self, code: str) -> Product | None:
        """Return a product by its unique code."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM products WHERE code = ?",
                (code.strip().upper(),),
            ).fetchone()
        return Product.from_row(row) if row else None

    def list_products(self, search: str | None = None) -> list[Product]:
        """Return all products or products matching a search query."""
        query = "SELECT * FROM products"
        params: list[str] = []

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query += " WHERE name LIKE ? OR code LIKE ? OR category LIKE ?"
            params.extend([pattern, pattern, pattern])

        query += " ORDER BY created_at DESC, name ASC"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Product.from_row(row) for row in rows]

    def add_stock(self, product_id: int, quantity: int) -> Product:
        """Increase available stock for a product."""
        if quantity <= 0:
            raise ValueError("Stock quantity must be greater than zero.")

        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")

        return self.update_product(
            product_id,
            product.name,
            product.category,
            product.price,
            product.quantity + quantity,
            product.description,
        )

    def reduce_stock(self, product_id: int, quantity: int) -> Product:
        """Reduce stock while preventing negative values."""
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        product = self.get_product_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")
        if product.quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.code}'. "
                f"Available: {product.quantity}, requested: {quantity}."
            )

        return self.update_product(
            product_id,
            product.name,
            product.category,
            product.price,
            product.quantity - quantity,
            product.description,
        )

    def get_inventory_value(self) -> float:
        """Return the current inventory valuation."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(price * quantity), 0) AS total FROM products"
            ).fetchone()
        return float(row["total"])

    def get_low_stock_products(self) -> list[Product]:
        """Return products at or below the low stock threshold."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM products
                WHERE quantity <= ?
                ORDER BY quantity ASC, name ASC
                """,
                (Config.LOW_STOCK_THRESHOLD,),
            ).fetchall()
        return [Product.from_row(row) for row in rows]

    def dashboard_summary(self) -> dict[str, object]:
        """Return core inventory metrics for the dashboard."""
        products = self.list_products()
        return {
            "total_products": len(products),
            "total_stock_units": sum(product.quantity for product in products),
            "total_stock_value": self.get_inventory_value(),
            "low_stock_products": self.get_low_stock_products(),
        }

    @staticmethod
    def _validate_product_fields(
        name: str,
        code: str,
        category: str,
        price: float,
        quantity: int,
    ) -> None:
        """Validate product fields before persistence."""
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
