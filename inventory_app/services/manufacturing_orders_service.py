"""Service layer for manufacturing order workflows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from database.db import get_connection
from database.models import Product, utc_now_iso
from services.inventory_service import InventoryService


@dataclass(frozen=True, slots=True)
class ManufacturingOrderItem:
    id: int
    manufacturing_order_id: int
    product_code: str
    ordered_quantity: int
    received_quantity: int
    pending_quantity: int


@dataclass(frozen=True, slots=True)
class ManufacturingOrder:
    id: int
    order_number: str
    created_at: str
    status: str
    notes: str | None
    items: list[ManufacturingOrderItem]


class ManufacturingOrdersService:
    """Encapsulates manufacturing order CRUD and delivery reception."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()

    def create_order(self, product_code: str, ordered_quantity: int, notes: str = "") -> ManufacturingOrder:
        product_code = (product_code or "").strip().upper()
        if not product_code:
            raise ValueError("Product code is required.")
        if ordered_quantity <= 0:
            raise ValueError("Ordered quantity must be greater than zero.")

        product = self.inventory_service.get_product_by_code(product_code)
        if not product:
            raise ValueError("Product not found.")

        with get_connection() as connection:
            order_number = self._generate_next_order_number(connection)
            created_at = utc_now_iso()
            status = "pending"

            cursor = connection.execute(
                """
                INSERT INTO manufacturing_orders (order_number, created_at, status, notes)
                VALUES (?, ?, ?, ?)
                """,
                (order_number, created_at, status, (notes or "").strip() or None),
            )
            order_id = int(cursor.lastrowid)

            pending_quantity = int(ordered_quantity)

            connection.execute(
                """
                INSERT INTO manufacturing_order_items (
                    manufacturing_order_id, product_code,
                    ordered_quantity, received_quantity, pending_quantity
                ) VALUES (?, ?, ?, 0, ?)
                """,
                (order_id, product_code, int(ordered_quantity), pending_quantity),
            )
            connection.commit()

        return self.get_order_by_id(order_id)

    def list_orders(self) -> list[ManufacturingOrder]:
        with get_connection() as connection:
            order_rows = connection.execute(
                """
                SELECT id, order_number, created_at, status, notes
                FROM manufacturing_orders
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

            items_rows = connection.execute(
                """
                SELECT * FROM manufacturing_order_items
                ORDER BY id ASC
                """
            ).fetchall()

        items_by_order: dict[int, list[ManufacturingOrderItem]] = {}
        for r in items_rows:
            item = ManufacturingOrderItem(
                id=int(r["id"]),
                manufacturing_order_id=int(r["manufacturing_order_id"]),
                product_code=str(r["product_code"]),
                ordered_quantity=int(r["ordered_quantity"]),
                received_quantity=int(r["received_quantity"]),
                pending_quantity=int(r["pending_quantity"]),
            )
            items_by_order.setdefault(item.manufacturing_order_id, []).append(item)

        orders: list[ManufacturingOrder] = []
        for o in order_rows:
            orders.append(
                ManufacturingOrder(
                    id=int(o["id"]),
                    order_number=str(o["order_number"]),
                    created_at=str(o["created_at"]),
                    status=str(o["status"]),
                    notes=o["notes"],
                    items=items_by_order.get(int(o["id"]), []),
                )
            )
        return orders

    def get_order_by_id(self, order_id: int) -> ManufacturingOrder | None:
        with get_connection() as connection:
            o = connection.execute(
                """
                SELECT id, order_number, created_at, status, notes
                FROM manufacturing_orders WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
            if not o:
                return None

            item_rows = connection.execute(
                """
                SELECT * FROM manufacturing_order_items
                WHERE manufacturing_order_id = ?
                ORDER BY id ASC
                """,
                (order_id,),
            ).fetchall()

            items = [
                ManufacturingOrderItem(
                    id=int(r["id"]),
                    manufacturing_order_id=int(r["manufacturing_order_id"]),
                    product_code=str(r["product_code"]),
                    ordered_quantity=int(r["ordered_quantity"]),
                    received_quantity=int(r["received_quantity"]),
                    pending_quantity=int(r["pending_quantity"]),
                )
                for r in item_rows
            ]

        return ManufacturingOrder(
            id=int(o["id"]),
            order_number=str(o["order_number"]),
            created_at=str(o["created_at"]),
            status=str(o["status"]),
            notes=o["notes"],
            items=items,
        )

    def receive_delivery(self, order_item_id: int, delivered_quantity: int) -> None:
        if delivered_quantity <= 0:
            raise ValueError("Delivered quantity must be greater than zero.")

        with get_connection() as connection:
            connection.row_factory = sqlite3.Row

            # Lock/validate item
            item_row = connection.execute(
                """
                SELECT * FROM manufacturing_order_items WHERE id = ?
                """,
                (order_item_id,),
            ).fetchone()
            if not item_row:
                raise ValueError("Manufacturing order item not found.")

            pending_quantity = int(item_row["pending_quantity"])
            received_quantity = int(item_row["received_quantity"])
            ordered_quantity = int(item_row["ordered_quantity"])
            product_code = str(item_row["product_code"])
            mo_id = int(item_row["manufacturing_order_id"])

            if delivered_quantity > pending_quantity:
                raise ValueError(
                    "Delivered quantity cannot exceed pending quantity. "
                    f"Pending: {pending_quantity}, Provided: {delivered_quantity}."
                )

            new_received = received_quantity + delivered_quantity
            new_pending = ordered_quantity - new_received

            # Write delivery history
            connection.execute(
                """
                INSERT INTO manufacturing_deliveries (
                    manufacturing_order_item_id, delivered_quantity, delivered_at
                ) VALUES (?, ?, ?)
                """,
                (order_item_id, delivered_quantity, utc_now_iso()),
            )

            # Update item quantities
            connection.execute(
                """
                UPDATE manufacturing_order_items
                SET received_quantity = ?, pending_quantity = ?
                WHERE id = ?
                """,
                (new_received, new_pending, order_item_id),
            )

            # Update products stock inside the same DB transaction to avoid SQLite locking.
            product_row = connection.execute(
                "SELECT id FROM products WHERE code = ?",
                (product_code,),
            ).fetchone()
            if not product_row:
                raise ValueError("Product not found for manufacturing item.")

            connection.execute(
                "UPDATE products SET quantity = quantity + ? WHERE id = ?",
                (delivered_quantity, int(product_row["id"])),
            )



            # Recompute order status based on all its items

            connection.execute(
                """
                UPDATE manufacturing_orders
                SET status = (
                    CASE
                        WHEN (
                            SELECT SUM(pending_quantity)
                            FROM manufacturing_order_items
                            WHERE manufacturing_order_id = manufacturing_orders.id
                        ) <= 0 THEN 'completed'
                        WHEN (
                            SELECT SUM(received_quantity)
                            FROM manufacturing_order_items
                            WHERE manufacturing_order_id = manufacturing_orders.id
                        ) > 0 THEN 'partial'
                        ELSE 'pending'
                    END
                )
                WHERE id = ?
                """,
                (mo_id,),
            )

            connection.commit()

    def get_deliveries_for_item(self, order_item_id: int) -> list[dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT delivered_quantity, delivered_at
                FROM manufacturing_deliveries
                WHERE manufacturing_order_item_id = ?
                ORDER BY delivered_at DESC, id DESC
                """,
                (order_item_id,),
            ).fetchall()

        return [
            {
                "delivered_quantity": int(r["delivered_quantity"]),
                "delivered_at": str(r["delivered_at"]),
            }
            for r in rows
        ]

    def search_and_filter_orders(
        self,
        search: str = "",
        status: str = "all",
    ) -> list[ManufacturingOrder]:
        """Search by product code/name (best-effort) and/or order number; apply status filter."""
        search = (search or "").strip()
        status = (status or "all").strip().lower()

        with get_connection() as connection:
            # Base: order header
            base = """
                SELECT mo.id, mo.order_number, mo.created_at, mo.status, mo.notes
                FROM manufacturing_orders mo
            """
            joins = """
                LEFT JOIN manufacturing_order_items moi ON moi.manufacturing_order_id = mo.id
                LEFT JOIN products p ON p.code = moi.product_code
            """
            where = ["1=1"]
            params: list[object] = []

            if status in {"pending", "partial", "completed"}:
                # Map UI status to db status
                db_status = status
                where.append("mo.status = ?")
                params.append(db_status)

            if search:
                pattern = f"%{search}%"
                # search by order number OR product_code OR product name
                where.append(
                    "(mo.order_number LIKE ? OR moi.product_code LIKE ? OR p.name LIKE ?)"
                )
                params.extend([pattern, pattern, pattern])

            query = (
                base + joins + " WHERE " + " AND ".join(where) + " GROUP BY mo.id "
                + " ORDER BY mo.created_at DESC, mo.id DESC"
            )
            order_rows = connection.execute(query, params).fetchall()

            order_ids = [int(r["id"]) for r in order_rows]
            items_by_order: dict[int, list[ManufacturingOrderItem]] = {oid: [] for oid in order_ids}

            if order_ids:
                placeholders = ",".join(["?"] * len(order_ids))
                items_rows = connection.execute(
                    f"""
                        SELECT *
                        FROM manufacturing_order_items
                        WHERE manufacturing_order_id IN ({placeholders})
                        ORDER BY id ASC
                    """,
                    order_ids,
                ).fetchall()

                for r in items_rows:
                    item = ManufacturingOrderItem(
                        id=int(r["id"]),
                        manufacturing_order_id=int(r["manufacturing_order_id"]),
                        product_code=str(r["product_code"]),
                        ordered_quantity=int(r["ordered_quantity"]),
                        received_quantity=int(r["received_quantity"]),
                        pending_quantity=int(r["pending_quantity"]),
                    )
                    items_by_order.setdefault(item.manufacturing_order_id, []).append(item)

        orders: list[ManufacturingOrder] = []
        for o in order_rows:
            oid = int(o["id"])
            orders.append(
                ManufacturingOrder(
                    id=oid,
                    order_number=str(o["order_number"]),
                    created_at=str(o["created_at"]),
                    status=str(o["status"]),
                    notes=o["notes"],
                    items=items_by_order.get(oid, []),
                )
            )
        return orders

    def get_orders_status_counts(self) -> dict[str, int]:
        """Counts for UI badges."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                    SELECT status, COUNT(*) as cnt
                    FROM manufacturing_orders
                    GROUP BY status
                """
            ).fetchall()

        counts = {"pending": 0, "partial": 0, "completed": 0}
        for r in rows:
            status = str(r["status"])
            if status in counts:
                counts[status] = int(r["cnt"])
        return counts

    @staticmethod
    def _generate_next_order_number(connection: sqlite3.Connection) -> str:
        """Auto-generated manufacturing order number (example: MFG-00001)."""
        row = connection.execute(
            "SELECT COALESCE(MAX(id), 0) as max_id FROM manufacturing_orders"
        ).fetchone()
        next_id = int(row["max_id"]) + 1
        return f"MFG-{next_id:05d}"


