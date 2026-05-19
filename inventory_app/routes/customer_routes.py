"""Routes for customer management."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.customer_service import CustomerService
from services.payment_service import PaymentService
from services.sales_service import SalesService
from utils.auth import login_required


customer_bp = Blueprint("customers", __name__, url_prefix="/customers")


@customer_bp.route("/", methods=["GET", "POST"])
@login_required
def customers() -> str:
    """Render customers page and handle customer creation."""
    customer_service = CustomerService()
    search = request.args.get("search", "").strip()

    if request.method == "POST":
        try:
            customer = customer_service.add_customer(
                request.form.get("name", ""),
                request.form.get("phone", ""),
                request.form.get("address", ""),
            )
            flash("Customer added successfully. Create the booking now.", "success")
            return redirect(url_for("preorders.preorders", customer_id=customer.id))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template(
        "customers.html",
        customers=customer_service.list_customers(search=search),
        search=search,
    )


@customer_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit_customer(customer_id: int) -> str:
    """Render and process customer edit form."""
    customer_service = CustomerService()
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("customers.customers"))

    if request.method == "POST":
        try:
            customer_service.update_customer(
                customer_id,
                request.form.get("name", ""),
                request.form.get("phone", ""),
                request.form.get("address", ""),
            )
            flash("Customer updated successfully.", "success")
            return redirect(url_for("customers.customers"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("edit_customer.html", customer=customer)


@customer_bp.route("/<int:customer_id>", methods=["GET"])
@login_required
def customer_details(customer_id: int) -> str:
    """Render customer purchase totals and payment history."""
    customer_service = CustomerService()
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("customers.customers"))

    payment_service = PaymentService()
    sales = [sale for sale in SalesService().list_sales() if sale.customer_id == customer_id]
    return render_template(
        "customer_details.html",
        customer=customer,
        sales=sales,
        payments=payment_service.list_payments_for_customer(customer_id),
        payment_summary=payment_service.get_customer_payment_summary(customer_id),
    )


@customer_bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete_customer(customer_id: int):
    """Delete a customer."""
    try:
        CustomerService().delete_customer(customer_id)
        flash("Customer deleted successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("customers.customers"))
