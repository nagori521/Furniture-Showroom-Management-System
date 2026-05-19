"""Preorder service for reservation and fulfillment workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from database.db import get_connection
from database.models import Preorder
from services.inventory_service import InventoryService


class PreorderService:
    """Handles product preorders and reserved stock tracking."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()

    def create_preorder(
        self, product_code: str, customer_name: str, quantity: int
    ) -> Preorder:
        """Reserve stock and create a preorder record."""
        if not customer_name.strip():
            raise ValueError("Customer name is required.")
        if quantity <= 0:
            raise ValueError("Preorder quantity must be greater than zero.")

        product = self.inventory_service.get_product_by_code(product_code)
        if not product:
            raise ValueError(f"Product with code '{product_code}' was not found.")

        self.inventory_service.reduce_stock(product.code, quantity)
        created_at = datetime.now(UTC).isoformat(timespec="seconds")

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO preorders (
                    product_code, customer_name, quantity, status, created_at
                ) VALUES (?, ?, ?, 'pending', ?)
                """,
                (product.code, customer_name.strip(), quantity, created_at),
            )
            connection.commit()
            preorder_id = cursor.lastrowid

        return Preorder(
            id=preorder_id,
            product_code=product.code,
            customer_name=customer_name.strip(),
            quantity=quantity,
            status="pending",
            created_at=created_at,
        )

    def update_preorder_status(self, preorder_id: int, status: str) -> Preorder:
        """Update preorder status to pending or delivered."""
        normalized_status = status.strip().lower()
        if normalized_status not in {"pending", "delivered"}:
            raise ValueError("Preorder status must be 'pending' or 'delivered'.")

        preorder = self.get_preorder_by_id(preorder_id)
        if not preorder:
            raise ValueError(f"Preorder with ID '{preorder_id}' was not found.")

        with get_connection() as connection:
            connection.execute(
                "UPDATE preorders SET status = ? WHERE id = ?",
                (normalized_status, preorder_id),
            )
            connection.commit()

        return self.get_preorder_by_id(preorder_id)

    def get_preorder_by_id(self, preorder_id: int) -> Preorder | None:
        """Fetch a preorder by its identifier."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM preorders WHERE id = ?",
                (preorder_id,),
            ).fetchone()
        return Preorder.from_row(row) if row else None

    def list_preorders(self, status: str | None = None) -> list[Preorder]:
        """Return preorders, optionally filtered by status."""
        query = "SELECT * FROM preorders"
        params: list[str] = []

        if status:
            query += " WHERE status = ?"
            params.append(status.strip().lower())

        query += " ORDER BY created_at DESC"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Preorder.from_row(row) for row in rows]

    def get_reserved_stock(self) -> dict[str, int]:
        """Return reserved stock per product code for pending preorders."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT product_code, SUM(quantity) AS reserved_quantity
                FROM preorders
                WHERE status = 'pending'
                GROUP BY product_code
                """
            ).fetchall()

        return {
            row["product_code"]: int(row["reserved_quantity"] or 0)
            for row in rows
        }

    def get_preorder_report(self) -> list[Preorder]:
        """Return all preorders for reporting."""
        return self.list_preorders()
