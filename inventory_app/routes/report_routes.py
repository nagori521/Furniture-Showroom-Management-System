"""Routes for management reports."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from services.report_service import ReportService
from utils.auth import login_required, role_required



report_bp = Blueprint("reports", __name__, url_prefix="/reports")


@report_bp.route("/", methods=["GET"])
@role_required("admin")
def reports() -> str:



    """Render the report dashboard."""
    report_service = ReportService()
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    return render_template(
        "reports.html",
        sales=report_service.get_sales_report(start_date, end_date),
        inventory=report_service.get_inventory_report(),
        deliveries=report_service.get_preorder_delivery_report(start_date, end_date),
        start_date=start_date or "",
        end_date=end_date or "",
    )
