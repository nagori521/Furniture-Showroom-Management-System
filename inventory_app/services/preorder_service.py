"""Preorder service for reservations and delivery tracking."""

from __future__ import annotations

from datetime import date
from sqlite3 import Connection

from database.db import get_connection
from database.models import Preorder, Product, utc_now_iso
from services.customer_service import CustomerService
from services.inventory_service import InventoryService


class PreorderService:
    """Handles preorder reservation rules."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()
        self.customer_service = CustomerService()

    def create_preorder(
        self,
        product_id: int,
        customer_id: int,
        quantity: int,
        delivery_date: str,
        discount_amount: float = 0,
        advance_paid: float = 0,
    ) -> Preorder:
        """Create a preorder and reserve stock immediately."""
        if quantity <= 0:
            raise ValueError("Preorder quantity must be greater than zero.")
        if discount_amount < 0:
            raise ValueError("Discount amount cannot be negative.")
        if advance_paid < 0:
            raise ValueError("Advance paid cannot be negative.")
        normalized_delivery_date = self._validate_delivery_date(delivery_date)

        customer = self.customer_service.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        with get_connection() as connection:
            product = self._get_product_for_update(connection, product_id)
            self._validate_stock(product, quantity)
            created_at = utc_now_iso()
            subtotal = product.price * quantity
            if discount_amount > subtotal:
                raise ValueError("Discount cannot exceed the preorder subtotal.")
            final_amount = subtotal - discount_amount
            if final_amount < 0:
                raise ValueError("Final amount cannot be negative.")
            if advance_paid > final_amount:
                raise ValueError("Advance paid cannot exceed the final amount.")
            pending_amount = final_amount - advance_paid

            connection.execute(
                "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                (quantity, product_id),
            )
            cursor = connection.execute(
                """
                INSERT INTO preorders (
                    product_id, customer_id, quantity, discount_amount, final_amount,
                    advance_paid, pending_amount,
                    delivery_date, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    product_id,
                    customer_id,
                    quantity,
                    discount_amount,
                    final_amount,
                    advance_paid,
                    pending_amount,
                    normalized_delivery_date,
                    created_at,
                ),
            )
            connection.commit()

        return self.get_preorder_by_id(int(cursor.lastrowid))

    def update_preorder_status(self, preorder_id: int, status: str) -> Preorder:
        """Update preorder status and re-apply reservation if needed."""
        normalized_status = status.strip().lower()
        if normalized_status not in {"pending", "delivered"}:
            raise ValueError("Status must be either 'pending' or 'delivered'.")

        preorder = self.get_preorder_by_id(preorder_id)
        if not preorder:
            raise ValueError("Preorder not found.")

        if preorder.status == normalized_status:
            return preorder

        if preorder.status == "delivered" and normalized_status == "pending":
            self.inventory_service.reduce_stock(preorder.product_id, preorder.quantity)

        with get_connection() as connection:
            connection.execute(
                "UPDATE preorders SET status = ? WHERE id = ?",
                (normalized_status, preorder_id),
            )
            connection.commit()

        return self.get_preorder_by_id(preorder_id)

    def get_preorder_by_id(self, preorder_id: int) -> Preorder | None:
        """Return a preorder by ID."""
        with get_connection() as connection:
            row = connection.execute(
                self._preorder_query() + " WHERE preorders.id = ?",
                (preorder_id,),
            ).fetchone()
        return Preorder.from_row(row) if row else None

    def list_preorders(
        self,
        limit: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
    ) -> list[Preorder]:
        """Return preorder history ordered by newest first."""
        query = self._preorder_query() + " WHERE 1 = 1"
        params: list[str] = []

        if start_date:
            query += " AND date(preorders.delivery_date) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(preorders.delivery_date) <= date(?)"
            params.append(end_date)
        if status and status != "all":
            query += " AND preorders.status = ?"
            params.append(status)

        query += " ORDER BY preorders.delivery_date ASC, preorders.created_at DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Preorder.from_row(row) for row in rows]

    def get_reserved_stock(self) -> dict[int, int]:
        """Return reserved quantity per product for pending preorders."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT product_id, COALESCE(SUM(quantity), 0) AS reserved_quantity
                FROM preorders
                WHERE status = 'pending'
                GROUP BY product_id
                """
            ).fetchall()

        return {
            int(row["product_id"]): int(row["reserved_quantity"])
            for row in rows
        }

    def get_upcoming_deliveries(self, limit: int = 5) -> list[Preorder]:
        """Return upcoming pending deliveries from today forward."""
        today = date.today().isoformat()
        query = (
            self._preorder_query()
            + """
            WHERE preorders.status = 'pending'
              AND date(preorders.delivery_date) >= date(?)
            ORDER BY preorders.delivery_date ASC, preorders.created_at ASC
            LIMIT ?
            """
        )
        with get_connection() as connection:
            rows = connection.execute(query, (today, limit)).fetchall()
        return [Preorder.from_row(row) for row in rows]

    def get_conversion_amounts(self, preorder_id: int) -> dict[str, float]:
        """Return preorder discount/final fields for future sale conversion."""
        preorder = self.get_preorder_by_id(preorder_id)
        if not preorder:
            raise ValueError("Preorder not found.")
        return {
            "discount_amount": preorder.discount_amount,
            "final_amount": preorder.final_total,
            "advance_paid": preorder.advance_paid,
            "pending_amount": preorder.pending_total,
            "subtotal": preorder.subtotal,
        }

    @staticmethod
    def _preorder_query() -> str:
        """Return the base joined preorder query."""
        return """
            SELECT
                preorders.*,
                products.name AS product_name,
                products.code AS product_code,
                products.price AS unit_price,
                customers.name AS customer_name,
                customers.phone AS customer_phone,
                customers.address AS customer_address
            FROM preorders
            JOIN products ON products.id = preorders.product_id
            JOIN customers ON customers.id = preorders.customer_id
        """

    @staticmethod
    def _validate_delivery_date(delivery_date: str) -> str:
        """Ensure delivery dates are provided and not in the past."""
        if not delivery_date:
            raise ValueError("Delivery date is required.")

        try:
            parsed_date = date.fromisoformat(delivery_date)
        except ValueError as exc:
            raise ValueError("Delivery date must be a valid date.") from exc

        if parsed_date < date.today():
            raise ValueError("Delivery date cannot be in the past.")

        return parsed_date.isoformat()

    @staticmethod
    def _get_product_for_update(connection: Connection, product_id: int) -> Product:
        """Fetch a product inside the current transaction."""
        row = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if not row:
            raise ValueError("Product not found.")
        return Product.from_row(row)

    @staticmethod
    def _validate_stock(product: Product, quantity: int) -> None:
        """Ensure a reservation cannot drive stock below zero."""
        if product.quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.code}'. "
                f"Available: {product.quantity}, requested: {quantity}."
            )
