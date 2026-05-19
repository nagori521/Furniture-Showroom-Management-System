"""Routes for manufacturing order creation and delivery reception."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.inventory_service import InventoryService
from services.manufacturing_orders_service import ManufacturingOrdersService
from utils.auth import login_required, role_required


manufacturing_orders_bp = Blueprint(
    "manufacturing_orders",
    __name__,
    url_prefix="/manufacturing-orders",
)


@manufacturing_orders_bp.route("/", methods=["GET", "POST"])
@login_required
@role_required("admin")
def list_orders():
    service = ManufacturingOrdersService()
    inventory_service = InventoryService()

    if request.method == "POST":
        try:
            product_code = (request.form.get("product_code") or "").strip().upper()
            ordered_quantity = int(request.form.get("ordered_quantity") or "0")
            notes = (request.form.get("notes") or "").strip()

            service.create_order(
                product_code=product_code,
                ordered_quantity=ordered_quantity,
                notes=notes,
            )
            flash("Manufacturing order created successfully.", "success")
            return redirect(url_for("manufacturing_orders.list_orders"))
        except ValueError as exc:
            flash(str(exc), "danger")

    search = (request.args.get("search") or "").strip()
    status = request.args.get("status") or "all"

    orders = service.search_and_filter_orders(search=search, status=status)
    products = inventory_service.list_products()

    # Smart counts for badges on the UI
    counts = service.get_orders_status_counts()
    return render_template(
        "manufacturing_orders.html",
        orders=orders,
        products=products,
        search=search,
        status=status,
        counts=counts,
    )



@manufacturing_orders_bp.route("/<int:order_id>", methods=["GET"])
@login_required
def order_details(order_id: int):
    service = ManufacturingOrdersService()
    inventory_service = InventoryService()

    order = service.get_order_by_id(order_id)
    if not order:
        flash("Manufacturing order not found.", "danger")
        return redirect(url_for("manufacturing_orders.list_orders"))

    # Add product names for display (best-effort)
    items_enriched: list[dict] = []
    for item in order.items:
        product = inventory_service.get_product_by_code(item.product_code)
        deliveries = service.get_deliveries_for_item(item.id)
        items_enriched.append(
            {
                "item": item,
                "product_name": product.name if product else item.product_code,
                "deliveries": deliveries,
            }
        )

    return render_template(
        "manufacturing_order_details.html",
        order=order,
        items=items_enriched,
    )


@manufacturing_orders_bp.route(
    "/<int:order_id>/items/<int:order_item_id>/receive",
    methods=["POST"],
)
@login_required
@role_required("admin")
def receive_delivery(order_id: int, order_item_id: int):
    service = ManufacturingOrdersService()

    try:
        delivered_quantity = int(request.form.get("delivered_quantity") or "0")
        service.receive_delivery(order_item_id=order_item_id, delivered_quantity=delivered_quantity)
        flash("Delivery received successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("manufacturing_orders.order_details", order_id=order_id))

