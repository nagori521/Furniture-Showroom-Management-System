"""Payment collection, pending balance, and customer ledger workflows."""

from __future__ import annotations

from datetime import date
from io import BytesIO, StringIO
import csv

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from config import Config
from database.db import get_connection
from database.models import PaymentHistory, Sale, utc_now_iso
from services.customer_service import CustomerService
from services.sales_service import SalesService
from services.payment_receipt_header_utils import draw_bill_header


class PaymentService:
    """Encapsulates pending payment and payment history operations."""

    PAYMENT_METHODS = {"Cash", "UPI", "Bank Transfer"}

    def __init__(self) -> None:
        self.sales_service = SalesService()
        self.customer_service = CustomerService()

    def list_pending_sales(self, search: str | None = None) -> list[Sale]:
        """Return all sales that still have pending balance."""
        query = self.sales_service._sale_query() + " WHERE sales.pending_amount > 0"
        params: list[str] = []
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query += """
                AND (
                    sales.invoice_number LIKE ?
                    OR customers.name LIKE ?
                    OR customers.phone LIKE ?
                    OR products.name LIKE ?
                    OR products.code LIKE ?
                )
            """
            params.extend([pattern, pattern, pattern, pattern, pattern])
        query += " ORDER BY sales.sold_at DESC"
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Sale.from_row(row) for row in rows]

    def list_payments_for_sale(self, sale_id: int) -> list[PaymentHistory]:
        """Return payment ledger items for a sale."""
        with get_connection() as connection:
            rows = connection.execute(
                self._payment_query() + " WHERE payment_history.sale_id = ? ORDER BY payment_history.payment_date DESC, payment_history.id DESC",
                (sale_id,),
            ).fetchall()
        return [PaymentHistory.from_row(row) for row in rows]

    def list_payments_for_customer(self, customer_id: int) -> list[PaymentHistory]:
        """Return payment ledger items for a customer."""
        with get_connection() as connection:
            rows = connection.execute(
                self._payment_query()
                + " WHERE payment_history.customer_id = ? ORDER BY payment_history.payment_date DESC, payment_history.id DESC",
                (customer_id,),
            ).fetchall()
        return [PaymentHistory.from_row(row) for row in rows]

    def add_payment(
        self,
        sale_id: int,
        payment_amount: float,
        payment_method: str,
        payment_note: str = "",
        payment_date: str | None = None,
    ) -> Sale:
        """Collect a partial payment and update the sale balance."""
        sale = self.sales_service.get_sale_by_id(sale_id)
        if not sale:
            raise ValueError("Sale not found.")
        if sale.pending_amount <= 0:
            raise ValueError("This invoice is already fully paid.")
        if payment_amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if payment_amount > sale.pending_amount:
            raise ValueError("Payment amount cannot be greater than the pending amount.")

        normalized_method = payment_method.strip()
        if normalized_method not in self.PAYMENT_METHODS:
            raise ValueError("Select a valid payment method.")

        normalized_date = self._normalize_payment_date(payment_date)
        created_at = utc_now_iso()
        new_paid = sale.advance_paid + payment_amount
        new_pending = max(sale.final_amount - new_paid, 0.0)
        payment_status = SalesService.calculate_payment_status(new_paid, new_pending)

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO payment_history (
                    sale_id, customer_id, payment_amount, payment_method,
                    payment_note, payment_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    sale.customer_id,
                    payment_amount,
                    normalized_method,
                    payment_note.strip(),
                    normalized_date,
                    created_at,
                ),
            )
            connection.execute(
                """
                UPDATE sales
                SET advance_paid = ?, pending_amount = ?, payment_status = ?
                WHERE id = ?
                """,
                (new_paid, new_pending, payment_status, sale_id),
            )
            connection.commit()

        return self.sales_service.get_sale_by_id(sale_id)

    def mark_fully_paid(
        self,
        sale_id: int,
        payment_method: str = "Cash",
        payment_note: str = "Marked fully paid from pending payments.",
    ) -> Sale:
        """Collect the remaining balance in one action."""
        sale = self.sales_service.get_sale_by_id(sale_id)
        if not sale:
            raise ValueError("Sale not found.")
        if sale.pending_amount <= 0:
            raise ValueError("This invoice is already fully paid.")
        return self.add_payment(sale_id, sale.pending_amount, payment_method, payment_note, date.today().isoformat())

    def get_customer_payment_summary(self, customer_id: int) -> dict[str, float]:
        """Return purchase, paid, and pending totals for one customer."""
        customer = self.customer_service.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(SUM(final_amount), 0) AS total_purchased,
                    COALESCE(SUM(advance_paid), 0) AS total_paid,
                    COALESCE(SUM(pending_amount), 0) AS total_pending
                FROM sales
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()
        return {
            "total_purchased": float(row["total_purchased"]),
            "total_paid": float(row["total_paid"]),
            "total_pending": float(row["total_pending"]),
        }

    def get_dashboard_metrics(self) -> dict[str, float | int]:
        """Return dashboard-ready payment metrics."""
        today = date.today().isoformat()
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COALESCE(SUM(pending_amount), 0) AS total_pending,
                    COUNT(DISTINCT CASE WHEN pending_amount > 0 THEN customer_id END) AS customers_pending
                FROM sales
                """
            ).fetchone()
            paid_today_row = connection.execute(
                """
                SELECT COALESCE(SUM(payment_amount), 0) AS paid_today
                FROM payment_history
                WHERE date(payment_date) = date(?)
                """,
                (today,),
            ).fetchone()
            delivery_row = connection.execute(
                """
                SELECT COUNT(*) AS pending_deliveries
                FROM preorders
                WHERE status = 'pending'
                """
            ).fetchone()
        return {
            "total_pending_amount": float(row["total_pending"]),
            "total_paid_today": float(paid_today_row["paid_today"]),
            "customers_with_pending": int(row["customers_pending"]),
            "pending_deliveries": int(delivery_row["pending_deliveries"]),
        }

    def get_pending_report(
        self,
        customer_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        payment_status: str | None = None,
    ) -> list[Sale]:
        """Return sales for pending payment reporting."""
        query = self.sales_service._sale_query() + " WHERE 1 = 1"
        params: list[str | int] = []
        if customer_id:
            query += " AND sales.customer_id = ?"
            params.append(customer_id)
        if start_date:
            query += " AND date(sales.sold_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(sales.sold_at) <= date(?)"
            params.append(end_date)
        if payment_status and payment_status != "all":
            query += " AND sales.payment_status = ?"
            params.append(payment_status)
        query += " ORDER BY sales.sold_at DESC"
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Sale.from_row(row) for row in rows]

    def generate_pending_report_csv(self, sales: list[Sale]) -> BytesIO:
        """Build a CSV report for pending payment records."""
        text_buffer = StringIO()
        writer = csv.writer(text_buffer)
        writer.writerow([
            "Invoice Number",
            "Customer Name",
            "Phone",
            "Product",
            "Final Amount",
            "Paid Amount",
            "Pending Amount",
            "Payment Status",
        ])
        for sale in sales:
            writer.writerow([
                sale.invoice_number,
                sale.customer_name,
                sale.customer_phone,
                sale.product_name,
                f"{sale.final_amount:.2f}",
                f"{sale.advance_paid:.2f}",
                f"{sale.pending_amount:.2f}",
                sale.payment_status,
            ])
        return BytesIO(text_buffer.getvalue().encode("utf-8-sig"))

    def generate_pending_report_pdf(self, sales: list[Sale]) -> BytesIO:
        """Build a compact PDF report for pending payment records."""
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 22 * mm
        pdf.setTitle("Pending Payment Report")
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(18 * mm, y, Config.SHOP_NAME)
        y -= 8 * mm
        pdf.setFont("Helvetica", 10)
        pdf.drawString(18 * mm, y, "Pending Payment Report")
        y -= 10 * mm
        pdf.setStrokeColor(colors.HexColor("#DDD6C4"))
        pdf.line(18 * mm, y, width - 18 * mm, y)
        y -= 8 * mm

        pdf.setFont("Helvetica-Bold", 8)
        headers = ["Invoice", "Customer", "Product", "Final", "Paid", "Pending", "Status"]
        xs = [18, 42, 78, 114, 136, 156, 178]
        for header, x in zip(headers, xs):
            pdf.drawString(x * mm, y, header)
        y -= 6 * mm

        pdf.setFont("Helvetica", 8)
        for sale in sales:
            if y < 24 * mm:
                pdf.showPage()
                y = height - 22 * mm
                pdf.setFont("Helvetica", 8)
            values = [
                sale.invoice_number,
                sale.customer_name[:18],
                sale.product_name[:18],
                f"{sale.final_amount:.0f}",
                f"{sale.advance_paid:.0f}",
                f"{sale.pending_amount:.0f}",
                sale.payment_status,
            ]
            for value, x in zip(values, xs):
                pdf.drawString(x * mm, y, str(value))
            y -= 6 * mm
        pdf.save()
        buffer.seek(0)
        return buffer

    def generate_payment_receipt_pdf(self, payment_id: int) -> BytesIO:
        """Generate a PDF receipt for one collected payment."""

        # Payment receipts need the same top branded banner as invoices.

        payment = self.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found.")

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = draw_bill_header(pdf, width, height)
        pdf.setTitle(f"Payment Receipt {payment.id}")

        pdf.setFont("Helvetica", 10)
        pdf.drawString(20 * mm, y, Config.SHOP_ADDRESS[:90])
        y -= 8 * mm
        pdf.drawString(20 * mm, y, f"Phone: {Config.SHOP_PHONE}")
        y -= 14 * mm
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(20 * mm, y, "Payment Receipt")
        y -= 12 * mm
        pdf.setFont("Helvetica", 10)
        rows = [
            ("Receipt No", f"PAY-{payment.id:05d}"),
            ("Invoice No", payment.invoice_number),
            ("Customer", f"{payment.customer_name} ({payment.customer_phone})"),
            ("Product", payment.product_name),
            ("Payment Date", payment.payment_date),
            ("Payment Method", payment.payment_method),
            ("Amount Paid", f"Rs. {payment.payment_amount:,.2f}"),
            ("Note", payment.payment_note or "-"),
        ]
        for label, value in rows:
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(24 * mm, y, f"{label}:")
            pdf.setFont("Helvetica", 10)
            pdf.drawString(62 * mm, y, str(value)[:82])
            y -= 8 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawString(20 * mm, 28 * mm, "This is a computer-generated payment receipt.")
        pdf.save()
        buffer.seek(0)
        return buffer

    def get_payment_by_id(self, payment_id: int) -> PaymentHistory | None:
        """Return one payment ledger entry."""
        with get_connection() as connection:
            row = connection.execute(
                self._payment_query() + " WHERE payment_history.id = ?",
                (payment_id,),
            ).fetchone()
        return PaymentHistory.from_row(row) if row else None

    @staticmethod
    def _normalize_payment_date(payment_date: str | None) -> str:
        """Validate and normalize payment date."""
        if not payment_date:
            return date.today().isoformat()
        try:
            return date.fromisoformat(payment_date).isoformat()
        except ValueError as exc:
            raise ValueError("Payment date must be a valid date.") from exc

    @staticmethod
    def _payment_query() -> str:
        """Return the base joined payment history query."""
        return """
            SELECT
                payment_history.*,
                sales.invoice_number,
                products.name AS product_name,
                customers.name AS customer_name,
                customers.phone AS customer_phone
            FROM payment_history
            JOIN sales ON sales.id = payment_history.sale_id
            JOIN products ON products.id = sales.product_id
            JOIN customers ON customers.id = payment_history.customer_id
        """
