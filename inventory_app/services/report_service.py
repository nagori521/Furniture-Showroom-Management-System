"""Reporting and invoice generation services."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from database.db import get_connection
from config import Config
from services.inventory_service import InventoryService
from services.preorder_service import PreorderService
from services.sales_service import SalesService


# Use the absolute path to the packaged static asset so ReportLab can always load it.
# (When started from a different working directory, relative paths often break.)
BILL_HEADER_PATH = Path(__file__).resolve().parents[1] / "static" / "img" / "bill-header.jpeg"



class ReportService:
    """Provides reporting and invoice export helpers."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()
        self.sales_service = SalesService()
        self.preorder_service = PreorderService()

    def get_sales_report(self, start_date: str | None, end_date: str | None):
        """Return sales within the provided date range."""
        return self.sales_service.list_sales(start_date=start_date, end_date=end_date)

    def get_inventory_report(self):
        """Return the full product catalog for reporting."""
        return self.inventory_service.list_products()

    def get_preorder_delivery_report(self, start_date: str | None, end_date: str | None):
        """Return preorders within the delivery date range."""
        return self.preorder_service.list_preorders(
            start_date=start_date,
            end_date=end_date,
        )

    def generate_invoice_pdf(self, sale_id: int) -> BytesIO:
        """Generate a PDF invoice for the provided sale."""
        sale = self.sales_service.get_sale_by_id(sale_id)
        if not sale:
            raise ValueError("Sale not found.")

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        pdf.setTitle(f"Invoice {sale.invoice_number}")
        y = self._draw_bill_header(pdf, width, height)
        y = self._draw_document_header(
            pdf,
            width,
            y,
            "Customer Invoice",
            sale.invoice_number,
            sale.sold_at[:10],
            None,
        )
        y = self._draw_customer_block(
            pdf,
            width,
            y,
            sale.customer_name,
            sale.customer_phone,
            sale.customer_address,
        )
        y = self._draw_items_table(
            pdf,
            width,
            y,
            sale.product_name,
            sale.quantity,
            sale.unit_price,
            sale.subtotal,
            sale.discount_amount,
            sale.final_total,
            sale.advance_paid,
            sale.pending_amount,
        )
        self._draw_document_footer(
            pdf,
            width,
            y,
            f"Pending Amount: Rs. {sale.pending_amount:,.2f}",
            "Thank you for choosing Vishal Bharat Furniture Works.",
        )
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return buffer

    def generate_preorder_bill_pdf(self, preorder_id: int) -> BytesIO:
        """Generate a PDF bill for a booking/preorder."""
        preorder = self.preorder_service.get_preorder_by_id(preorder_id)
        if not preorder:
            raise ValueError("Booking not found.")

        bill_number = f"BOOK-{preorder.id:05d}"
        subtotal = preorder.subtotal
        final_amount = preorder.final_total

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        pdf.setTitle(f"Booking Bill {bill_number}")
        y = self._draw_bill_header(pdf, width, height)
        y = self._draw_document_header(
            pdf,
            width,
            y,
            "Booking Bill",
            bill_number,
            preorder.created_at[:10],
            preorder.delivery_date,
        )
        y = self._draw_customer_block(
            pdf,
            width,
            y,
            preorder.customer_name,
            preorder.customer_phone,
            preorder.customer_address,
        )
        y = self._draw_items_table(
            pdf,
            width,
            y,
            preorder.product_name,
            preorder.quantity,
            preorder.unit_price,
            subtotal,
            preorder.discount_amount,
            final_amount,
            preorder.advance_paid,
            preorder.pending_amount,
        )
        self._draw_document_footer(
            pdf,
            width,
            y,
            f"Pending Amount: Rs. {preorder.pending_amount:,.2f}",
            "Your booking has been reserved for the scheduled delivery date.",
        )
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def _draw_bill_header(pdf: canvas.Canvas, width: float, height: float) -> float:
        """Draw the branded bill header and return the next content y-position."""
        header_width = width - 40 * mm
        header_height = header_width * (156 / 682)
        header_bottom = height - 18 * mm - header_height

        # ReportLab is sensitive to broken paths; always validate and fail gracefully.
        if BILL_HEADER_PATH.exists() and BILL_HEADER_PATH.is_file():
            pdf.drawImage(
                str(BILL_HEADER_PATH),
                20 * mm,
                header_bottom,
                width=header_width,
                height=header_height,
                preserveAspectRatio=True,
                mask="auto",
            )
            return header_bottom - 10 * mm

        # Fallback to keep PDF layout stable if the image can't be loaded.
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(20 * mm, height - 25 * mm, "Vishal Bharat Furniture Works")
        return height - 45 * mm

    @staticmethod
    def _draw_document_header(
        pdf: canvas.Canvas,
        width: float,
        y: float,
        document_title: str,
        document_number: str,
        document_date: str,
        delivery_date: str | None,
    ) -> float:
        """Draw bill title and metadata block."""
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(20 * mm, y, Config.SHOP_NAME)
        y -= 7 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawString(20 * mm, y, Config.SHOP_ADDRESS[:92])
        y -= 5 * mm
        pdf.drawString(20 * mm, y, f"Phone: {Config.SHOP_PHONE}")
        y -= 7 * mm
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(20 * mm, y, document_title)

        meta_top = y + 4 * mm
        meta_height = 20 * mm if delivery_date else 14 * mm
        meta_x = width - 75 * mm
        pdf.setStrokeColor(colors.HexColor("#DDD6C4"))
        pdf.setFillColor(colors.HexColor("#F7F4EC"))
        pdf.roundRect(meta_x, meta_top - meta_height, 55 * mm, meta_height, 3 * mm, stroke=1, fill=1)

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(meta_x + 4 * mm, meta_top - 5 * mm, f"No: {document_number}")
        pdf.drawString(meta_x + 4 * mm, meta_top - 10 * mm, f"Date: {document_date}")
        if delivery_date:
            pdf.drawString(meta_x + 4 * mm, meta_top - 15 * mm, f"Delivery: {delivery_date}")

        return y - 12 * mm

    @staticmethod
    def _draw_customer_block(
        pdf: canvas.Canvas,
        width: float,
        y: float,
        customer_name: str,
        customer_phone: str,
        customer_address: str,
    ) -> float:
        """Draw the billing section."""
        block_height = 24 * mm
        pdf.setStrokeColor(colors.HexColor("#DDD6C4"))
        pdf.roundRect(20 * mm, y - block_height, width - 40 * mm, block_height, 3 * mm, stroke=1, fill=0)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(24 * mm, y - 5 * mm, "Bill To")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(24 * mm, y - 11 * mm, f"Name: {customer_name}")
        pdf.drawString(24 * mm, y - 16 * mm, f"Phone: {customer_phone}")
        pdf.drawString(24 * mm, y - 21 * mm, f"Address: {customer_address[:68]}")
        return y - 30 * mm

    @staticmethod
    def _draw_items_table(
        pdf: canvas.Canvas,
        width: float,
        y: float,
        product_name: str,
        quantity: int,
        unit_price: float,
        subtotal: float,
        discount_amount: float,
        total_price: float,
        advance_paid: float,
        pending_amount: float,
    ) -> float:
        """Draw the line-item table for the invoice or bill."""
        left = 20 * mm
        table_width = width - 40 * mm
        header_height = 8 * mm
        row_height = 10 * mm
        header_bottom = y - header_height

        pdf.setFillColor(colors.HexColor("#F0E7D8"))
        pdf.rect(left, header_bottom, table_width, header_height, stroke=0, fill=1)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left + 3 * mm, y - 5.5 * mm, "Description")
        pdf.drawString(left + 92 * mm, y - 5.5 * mm, "Qty")
        pdf.drawString(left + 110 * mm, y - 5.5 * mm, "Price")
        pdf.drawString(left + 138 * mm, y - 5.5 * mm, "Subtotal")

        row_bottom = header_bottom - row_height
        pdf.setStrokeColor(colors.HexColor("#DDD6C4"))
        pdf.rect(left, row_bottom, table_width, header_height + row_height, stroke=1, fill=0)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left + 3 * mm, header_bottom - 6.5 * mm, product_name[:46])
        pdf.drawString(left + 92 * mm, header_bottom - 6.5 * mm, str(quantity))
        pdf.drawString(left + 110 * mm, header_bottom - 6.5 * mm, f"Rs. {unit_price:,.2f}")
        pdf.drawString(left + 138 * mm, header_bottom - 6.5 * mm, f"Rs. {subtotal:,.2f}")

        summary_top = row_bottom - 8 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - 20 * mm, summary_top, f"Subtotal: Rs. {subtotal:,.2f}")
        pdf.drawRightString(
            width - 20 * mm,
            summary_top - 5 * mm,
            f"Discount: Rs. {discount_amount:,.2f}",
        )
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(
            width - 20 * mm,
            summary_top - 11 * mm,
            f"Final Total: Rs. {total_price:,.2f}",
        )
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(
            width - 20 * mm,
            summary_top - 16 * mm,
            f"Advance Paid: Rs. {advance_paid:,.2f}",
        )
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(
            width - 20 * mm,
            summary_top - 22 * mm,
            f"Pending Amount: Rs. {pending_amount:,.2f}",
        )
        return summary_top - 29 * mm

    @staticmethod
    def _draw_document_footer(
        pdf: canvas.Canvas,
        width: float,
        y: float,
        total_label: str,
        footer_note: str,
    ) -> None:
        """Draw total and footer note."""
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(width - 20 * mm, y, total_label)
        y -= 12 * mm
        pdf.line(20 * mm, y, width - 20 * mm, y)
        y -= 8 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawString(20 * mm, y, footer_note)
        pdf.drawString(20 * mm, y - 5 * mm, "Thank you for your business.")
        pdf.drawString(20 * mm, y - 10 * mm, "This is a computer-generated furniture showroom bill.")
