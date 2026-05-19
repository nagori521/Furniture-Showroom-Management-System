"""Sales service for handling transactions and revenue reports."""

from __future__ import annotations

from datetime import UTC, datetime

from database.db import get_connection
from database.models import Sale
from services.inventory_service import InventoryService


class SalesService:
    """Provides sales operations for the furniture business."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()

    def record_sale(self, product_code: str, quantity: int) -> Sale:
        """Create a sale and reduce inventory stock."""
        if quantity <= 0:
            raise ValueError("Sale quantity must be greater than zero.")

        product = self.inventory_service.get_product_by_code(product_code)
        if not product:
            raise ValueError(f"Product with code '{product_code}' was not found.")

        self.inventory_service.reduce_stock(product.code, quantity)
        total_price = product.price * quantity
        sold_at = datetime.now(UTC).isoformat(timespec="seconds")

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sales (product_code, quantity, total_price, sold_at)
                VALUES (?, ?, ?, ?)
                """,
                (product.code, quantity, total_price, sold_at),
            )
            connection.commit()
            sale_id = cursor.lastrowid

        return Sale(
            id=sale_id,
            product_code=product.code,
            quantity=quantity,
            total_price=total_price,
            sold_at=sold_at,
        )

    def list_sales(self) -> list[Sale]:
        """Return the full sales history."""
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM sales ORDER BY sold_at DESC"
            ).fetchall()
        return [Sale.from_row(row) for row in rows]

    def get_total_revenue(self) -> float:
        """Return cumulative revenue from all recorded sales."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(total_price), 0) AS total_revenue FROM sales"
            ).fetchone()
        return float(row["total_revenue"])

    def get_sales_report(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> list[Sale]:
        """Return sales between optional ISO date boundaries."""
        query = "SELECT * FROM sales WHERE 1 = 1"
        params: list[str] = []

        if start_date:
            query += " AND date(sold_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(sold_at) <= date(?)"
            params.append(end_date)

        query += " ORDER BY sold_at DESC"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Sale.from_row(row) for row in rows]
