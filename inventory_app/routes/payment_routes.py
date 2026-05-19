"""Routes for pending payment collection and reporting."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from services.customer_service import CustomerService
from services.payment_service import PaymentService
from services.sales_service import SalesService
from utils.auth import login_required


payment_bp = Blueprint("payments", __name__, url_prefix="/pending-payments")


@payment_bp.route("/", methods=["GET"])
@login_required
def pending_payments() -> str:
    """Render all invoices with a pending balance."""
    search = request.args.get("search", "").strip()
    payment_service = PaymentService()
    return render_template(
        "pending_payments.html",
        pending_sales=payment_service.list_pending_sales(search=search),
        search=search,
        today=date.today().isoformat(),
    )


@payment_bp.route("/<int:sale_id>", methods=["GET"])
@login_required
def payment_details(sale_id: int) -> str:
    """Render one invoice payment timeline."""
    sale = SalesService().get_sale_by_id(sale_id)
    if not sale:
        flash("Sale not found.", "danger")
        return redirect(url_for("payments.pending_payments"))
    payment_service = PaymentService()
    return render_template(
        "payment_history.html",
        sale=sale,
        payments=payment_service.list_payments_for_sale(sale_id),
        today=date.today().isoformat(),
    )


@payment_bp.route("/<int:sale_id>/add", methods=["POST"])
@login_required
def add_payment(sale_id: int):
    """Collect an invoice payment."""
    try:
        amount = float(request.form.get("payment_amount", "0") or "0")
        sale = PaymentService().add_payment(
            sale_id=sale_id,
            payment_amount=amount,
            payment_method=request.form.get("payment_method", ""),
            payment_note=request.form.get("payment_note", ""),
            payment_date=request.form.get("payment_date", ""),
        )
        flash(
            f"Payment recorded for {sale.invoice_number}. Pending balance is Rs. {sale.pending_amount:.2f}.",
            "success",
        )
    except ValueError as exc:
        flash(str(exc), "danger")

    next_url = request.form.get("next") or url_for("payments.pending_payments")
    return redirect(next_url)


@payment_bp.route("/<int:sale_id>/mark-paid", methods=["POST"])
@login_required
def mark_fully_paid(sale_id: int):
    """Mark the invoice fully paid by collecting the remaining balance."""
    try:
        sale = PaymentService().mark_fully_paid(
            sale_id,
            request.form.get("payment_method", "Cash"),
            request.form.get("payment_note", "Marked fully paid."),
        )
        flash(f"Invoice {sale.invoice_number} is now fully paid.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    next_url = request.form.get("next") or url_for("payments.pending_payments")
    return redirect(next_url)


@payment_bp.route("/report", methods=["GET"])
@login_required
def pending_report() -> str:
    """Render the pending payment report screen."""
    payment_service = PaymentService()
    customer_id = request.args.get("customer_id", type=int)
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    payment_status = request.args.get("payment_status", "all")
    return render_template(
        "pending_payment_report.html",
        report_sales=payment_service.get_pending_report(customer_id, start_date, end_date, payment_status),
        customers=CustomerService().list_customers(),
        customer_id=customer_id,
        start_date=start_date or "",
        end_date=end_date or "",
        payment_status=payment_status,
    )


@payment_bp.route("/report.csv", methods=["GET"])
@login_required
def pending_report_csv():
    """Download pending payment report as CSV."""
    payment_service = PaymentService()
    sales = payment_service.get_pending_report(
        request.args.get("customer_id", type=int),
        request.args.get("start_date") or None,
        request.args.get("end_date") or None,
        request.args.get("payment_status", "all"),
    )
    return send_file(
        payment_service.generate_pending_report_csv(sales),
        mimetype="text/csv",
        as_attachment=True,
        download_name="pending-payment-report.csv",
    )


@payment_bp.route("/report.pdf", methods=["GET"])
@login_required
def pending_report_pdf():
    """Download pending payment report as PDF."""
    payment_service = PaymentService()
    sales = payment_service.get_pending_report(
        request.args.get("customer_id", type=int),
        request.args.get("start_date") or None,
        request.args.get("end_date") or None,
        request.args.get("payment_status", "all"),
    )
    return send_file(
        payment_service.generate_pending_report_pdf(sales),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="pending-payment-report.pdf",
    )


@payment_bp.route("/receipt/<int:payment_id>.pdf", methods=["GET"])
@login_required
def payment_receipt(payment_id: int):
    """Download one payment receipt as PDF."""
    try:
        return send_file(
            PaymentService().generate_payment_receipt_pdf(payment_id),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"payment-receipt-{payment_id:05d}.pdf",
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("payments.pending_payments"))
