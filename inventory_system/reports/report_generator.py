"""Generate textual reports for inventory, sales, and preorders."""

from __future__ import annotations

from services.inventory_service import InventoryService
from services.preorder_service import PreorderService
from services.sales_service import SalesService
from utils.helpers import format_currency, format_datetime


class ReportGenerator:
    """Builds readable reports for business operations."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()
        self.sales_service = SalesService()
        self.preorder_service = PreorderService()

    def generate_sales_report(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> str:
        """Generate a sales report for an optional date range."""
        sales = self.sales_service.get_sales_report(start_date, end_date)
        lines = ["Sales Report", "-" * 60]

        if start_date or end_date:
            lines.append(
                f"Filter: {start_date or 'Beginning'} to {end_date or 'Today'}"
            )

        if not sales:
            lines.append("No sales found for the selected date range.")
            return "\n".join(lines)

        total_revenue = 0.0
        for sale in sales:
            total_revenue += sale.total_price
            lines.append(
                f"{format_datetime(sale.sold_at)} | {sale.product_code} | "
                f"Qty: {sale.quantity} | Amount: {format_currency(sale.total_price)}"
            )

        lines.append("-" * 60)
        lines.append(f"Total Revenue: {format_currency(total_revenue)}")
        return "\n".join(lines)

    def generate_inventory_report(self) -> str:
        """Generate a report of products, stock, and valuation."""
        products = self.inventory_service.list_products()
        reserved = self.preorder_service.get_reserved_stock()
        lines = ["Inventory Report", "-" * 60]

        if not products:
            lines.append("No products available in inventory.")
            return "\n".join(lines)

        for product in products:
            reserved_qty = reserved.get(product.code, 0)
            lines.append(
                f"{product.code} | {product.name} | {product.category} | "
                f"Price: {format_currency(product.price)} | "
                f"Available: {product.quantity} | Reserved: {reserved_qty}"
            )

        lines.append("-" * 60)
        lines.append(
            f"Total Inventory Value: "
            f"{format_currency(self.inventory_service.get_inventory_value())}"
        )
        return "\n".join(lines)

    def generate_preorder_report(self) -> str:
        """Generate a report of all preorder activity."""
        preorders = self.preorder_service.get_preorder_report()
        lines = ["Preorder Report", "-" * 60]

        if not preorders:
            lines.append("No preorder records found.")
            return "\n".join(lines)

        for preorder in preorders:
            lines.append(
                f"#{preorder.id} | {preorder.customer_name} | "
                f"{preorder.product_code} | Qty: {preorder.quantity} | "
                f"Status: {preorder.status} | "
                f"{format_datetime(preorder.created_at)}"
            )

        return "\n".join(lines)
