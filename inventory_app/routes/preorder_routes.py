"""Routes for preorder creation and status updates."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from services.customer_service import CustomerService
from services.inventory_service import InventoryService
from services.preorder_service import PreorderService
from services.report_service import ReportService
from utils.auth import login_required


preorder_bp = Blueprint("preorders", __name__, url_prefix="/preorders")


def _resolve_customer_from_request(customer_service: CustomerService):
    """Resolve the selected or inline-created customer from form data."""
    customer_choice = request.form.get("customer_choice", "existing").strip()
    customer_id = request.form.get("customer_id", type=int)

    if customer_choice == "new":
        return customer_service.resolve_customer(
            name=request.form.get("customer_name", ""),
            phone=request.form.get("customer_phone", ""),
            address=request.form.get("customer_address", ""),
        )

    return customer_service.resolve_customer(customer_id=customer_id)


@preorder_bp.route("/", methods=["GET", "POST"])
@login_required
def preorders() -> str:
    """Render preorder page and handle preorder creation."""
    inventory_service = InventoryService()
    customer_service = CustomerService()
    preorder_service = PreorderService()
    selected_customer_id = request.args.get("customer_id", type=int)
    status_filter = request.args.get("status", "all").strip().lower()

    if status_filter not in {"all", "pending", "delivered"}:
        status_filter = "all"

    if request.method == "POST":
        try:
            product_id = int(request.form.get("product_id", "0"))
            quantity = int(request.form.get("quantity", "0"))
            discount_amount_raw = request.form.get("discount_amount", "0") or "0"
            try:
                discount_amount = float(discount_amount_raw)
            except ValueError as exc:
                raise ValueError("Discount amount must be a valid number.") from exc
            advance_paid_raw = request.form.get("advance_paid", "0") or "0"
            try:
                advance_paid = float(advance_paid_raw)
            except ValueError as exc:
                raise ValueError("Advance paid must be a valid number.") from exc
            delivery_date = request.form.get("delivery_date", "").strip()
            customer = _resolve_customer_from_request(customer_service)
            preorder = preorder_service.create_preorder(
                product_id,
                customer.id,
                quantity,
                delivery_date,
                discount_amount,
                advance_paid,
            )
            flash("Booking created successfully. Bill is ready.", "success")
            return redirect(url_for("preorders.view_bill", preorder_id=preorder.id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "preorders.html",
        products=inventory_service.list_products(),
        customers=customer_service.list_customers(),
        preorders=preorder_service.list_preorders(status=status_filter),
        upcoming_deliveries=preorder_service.get_upcoming_deliveries(limit=10),
        selected_customer_id=selected_customer_id,
        status_filter=status_filter,
    )


@preorder_bp.route("/<int:preorder_id>/bill")
@login_required
def view_bill(preorder_id: int) -> str:
    """Render a booking bill."""
    preorder = PreorderService().get_preorder_by_id(preorder_id)
    if not preorder:
        flash("Booking not found.", "danger")
        return redirect(url_for("preorders.preorders"))
    return render_template("booking_bill.html", preorder=preorder)


@preorder_bp.route("/<int:preorder_id>/bill.pdf")
@login_required
def download_bill(preorder_id: int):
    """Download a PDF booking bill."""
    try:
        pdf_buffer = ReportService().generate_preorder_bill_pdf(preorder_id)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"BOOK-{preorder_id:05d}.pdf",
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("preorders.preorders"))


@preorder_bp.route("/<int:preorder_id>/status", methods=["POST"])
@login_required
def update_status(preorder_id: int):
    """Update preorder status and redirect back to the preorder page."""
    preorder_service = PreorderService()

    try:
        status = request.form.get("status", "").strip()
        preorder_service.update_preorder_status(preorder_id, status)
        flash("Preorder status updated successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("preorders.preorders"))
