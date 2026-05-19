"""Sales service for customer transactions and invoice metadata."""

from __future__ import annotations

from sqlite3 import Connection

from database.db import get_connection
from database.models import Product, Sale, utc_now_iso
from services.customer_service import CustomerService
from services.inventory_service import InventoryService


class SalesService:
    """Encapsulates sales workflows."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()
        self.customer_service = CustomerService()

    def record_sale(
        self,
        product_id: int,
        customer_id: int,
        quantity: int,
        discount_amount: float = 0,
        advance_paid: float = 0,
    ) -> Sale:
        """Record a sale and reduce product stock."""
        if quantity <= 0:
            raise ValueError("Sale quantity must be greater than zero.")
        if discount_amount < 0:
            raise ValueError("Discount amount cannot be negative.")
        if advance_paid < 0:
            raise ValueError("Advance paid cannot be negative.")

        customer = self.customer_service.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        with get_connection() as connection:
            product = self._get_product_for_update(connection, product_id)
            self._validate_stock(product, quantity)
            sold_at = utc_now_iso()
            unit_price = product.price
            subtotal = product.price * quantity
            if discount_amount > subtotal:
                raise ValueError("Discount cannot exceed the sale subtotal.")
            final_amount = subtotal - discount_amount
            if final_amount < 0:
                raise ValueError("Final total cannot be negative.")
            if advance_paid > final_amount:
                raise ValueError("Advance paid cannot exceed the final amount.")
            pending_amount = final_amount - advance_paid
            payment_status = self.calculate_payment_status(advance_paid, pending_amount)

            connection.execute(
                "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                (quantity, product_id),
            )
            cursor = connection.execute(
                """
                INSERT INTO sales (
                    product_id, customer_id, quantity, unit_price, total_price,
                    final_amount, discount_amount, advance_paid, pending_amount,
                    payment_status, invoice_number, sold_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    customer_id,
                    quantity,
                    unit_price,
                    subtotal,
                    final_amount,
                    discount_amount,
                    advance_paid,
                    pending_amount,
                    payment_status,
                    "PENDING",
                    sold_at,
                ),
            )
            sale_id = int(cursor.lastrowid)
            invoice_number = f"INV-{sale_id:05d}"
            connection.execute(
                "UPDATE sales SET invoice_number = ? WHERE id = ?",
                (invoice_number, sale_id),
            )
            if advance_paid > 0:
                connection.execute(
                    """
                    INSERT INTO payment_history (
                        sale_id, customer_id, payment_amount, payment_method,
                        payment_note, payment_date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        customer_id,
                        advance_paid,
                        "Cash",
                        "Initial advance payment recorded during sale.",
                        sold_at[:10],
                        sold_at,
                    ),
                )
            connection.commit()

        return self.get_sale_by_id(sale_id)

    def get_sale_by_id(self, sale_id: int) -> Sale | None:
        """Return a sale by ID."""
        with get_connection() as connection:
            row = connection.execute(
                self._sale_query() + " WHERE sales.id = ?",
                (sale_id,),
            ).fetchone()
        return Sale.from_row(row) if row else None

    def list_sales(
        self,
        limit: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Sale]:
        """Return sales history ordered by newest first."""
        query = self._sale_query() + " WHERE 1 = 1"
        params: list[str] = []

        if start_date:
            query += " AND date(sales.sold_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(sales.sold_at) <= date(?)"
            params.append(end_date)

        query += " ORDER BY sales.sold_at DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Sale.from_row(row) for row in rows]

    def get_total_revenue(self) -> float:
        """Return total revenue across all sales."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(final_amount), 0) AS total_revenue FROM sales"
            ).fetchone()
        return float(row["total_revenue"])

    def get_total_sales_count(self) -> int:
        """Return total sales transaction count."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total_sales FROM sales"
            ).fetchone()
        return int(row["total_sales"])

    @staticmethod
    def calculate_payment_status(paid_amount: float, pending_amount: float) -> str:
        """Return Paid, Partial, or Pending for a payment state."""
        if pending_amount <= 0:
            return "Paid"
        if paid_amount > 0:
            return "Partial"
        return "Pending"

    @staticmethod
    def _sale_query() -> str:
        """Return the base joined sales query."""
        return """
            SELECT
                sales.*,
                products.name AS product_name,
                products.code AS product_code,
                customers.name AS customer_name,
                customers.phone AS customer_phone,
                customers.address AS customer_address
            FROM sales
            JOIN products ON products.id = sales.product_id
            JOIN customers ON customers.id = sales.customer_id
        """

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
        """Ensure a sale cannot drive stock below zero."""
        if product.quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.code}'. "
                f"Available: {product.quantity}, requested: {quantity}."
            )
