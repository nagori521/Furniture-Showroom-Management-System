"""Dashboard routes for overview metrics and recent activity."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, render_template

from services.customer_service import CustomerService
from services.inventory_service import InventoryService
from services.payment_service import PaymentService
from services.preorder_service import PreorderService
from services.sales_service import SalesService
from utils.auth import login_required


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required

def dashboard() -> str:

    """Render the main dashboard."""
    inventory_service = InventoryService()
    sales_service = SalesService()
    preorder_service = PreorderService()
    customer_service = CustomerService()
    payment_service = PaymentService()

    summary = inventory_service.dashboard_summary()
    sales = sales_service.list_sales(limit=5)
    preorders = preorder_service.list_preorders(limit=5)
    upcoming_deliveries = preorder_service.get_upcoming_deliveries(limit=10)

    recent_activity: list[dict[str, str]] = []
    for sale in sales:
        recent_activity.append(
            {
                "type": "Sale",
                "title": f"{sale.customer_name} bought {sale.product_name}",
                "meta": f"{sale.quantity} unit(s) | {sale.invoice_number}",
                "timestamp": sale.sold_at,
            }
        )
    for preorder in preorders:
        recent_activity.append(
            {
                "type": "Preorder",
                "title": f"{preorder.customer_name} reserved {preorder.product_name}",
                "meta": f"{preorder.quantity} unit(s) | Delivery {preorder.delivery_date}",
                "timestamp": preorder.created_at,
            }
        )

    recent_activity.sort(
        key=lambda item: datetime.fromisoformat(item["timestamp"]),
        reverse=True,
    )

    return render_template(
        "dashboard.html",
        summary=summary,
        total_revenue=sales_service.get_total_revenue(),
        total_sales=sales_service.get_total_sales_count(),
        total_customers=len(customer_service.list_customers()),
        upcoming_deliveries=upcoming_deliveries,
        upcoming_delivery_count=len(upcoming_deliveries),
        low_stock_count=len(summary["low_stock_products"]),
        recent_activity=recent_activity[:8],
        payment_metrics=payment_service.get_dashboard_metrics(),
    )
