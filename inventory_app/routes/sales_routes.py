"""Routes for recording, viewing, and invoicing sales."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from services.customer_service import CustomerService
from services.inventory_service import InventoryService
from services.report_service import ReportService
from services.sales_service import SalesService
from utils.auth import login_required


sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


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


@sales_bp.route("/", methods=["GET", "POST"])
@login_required
def sales() -> str:
    """Render sales page and handle sale recording."""
    inventory_service = InventoryService()
    customer_service = CustomerService()
    sales_service = SalesService()

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
            customer = _resolve_customer_from_request(customer_service)
            sale = sales_service.record_sale(
                product_id,
                customer.id,
                quantity,
                discount_amount,
                advance_paid,
            )
            flash(f"Sale recorded. Invoice {sale.invoice_number} created.", "success")
            return redirect(url_for("sales.view_invoice", sale_id=sale.id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "sales.html",
        products=inventory_service.list_products(),
        customers=customer_service.list_customers(),
        sales=sales_service.list_sales(),
        total_revenue=sales_service.get_total_revenue(),
    )


@sales_bp.route("/<int:sale_id>/invoice")
@login_required
def view_invoice(sale_id: int) -> str:
    """Render an HTML invoice."""
    sale = SalesService().get_sale_by_id(sale_id)
    if not sale:
        flash("Sale not found.", "danger")
        return redirect(url_for("sales.sales"))
    return render_template("invoice.html", sale=sale)


@sales_bp.route("/<int:sale_id>/invoice.pdf")
@login_required
def download_invoice(sale_id: int):
    """Download a PDF invoice."""
    try:
        pdf_buffer = ReportService().generate_invoice_pdf(sale_id)
        sale = SalesService().get_sale_by_id(sale_id)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{sale.invoice_number}.pdf",
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("sales.sales"))
