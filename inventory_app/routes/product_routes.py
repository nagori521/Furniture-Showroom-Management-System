"""Routes for product and stock management."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.inventory_service import InventoryService
from services.preorder_service import PreorderService
from utils.auth import login_required, role_required



product_bp = Blueprint("products", __name__, url_prefix="/products")


def _parse_product_form() -> tuple[str, str, str, float, int, str]:
    """Parse and normalize product form inputs."""
    return (
        request.form.get("name", "").strip(),
        request.form.get("code", "").strip(),
        request.form.get("category", "").strip(),
        float(request.form.get("price", "0")),
        int(request.form.get("quantity", "0")),
        request.form.get("description", "").strip(),
    )


@product_bp.route("/", methods=["GET"])
@login_required
def list_products() -> str:

    """Render the product list with optional search."""
    inventory_service = InventoryService()
    preorder_service = PreorderService()
    search = request.args.get("search", "").strip()

    return render_template(
        "products.html",
        products=inventory_service.list_products(search=search),
        reserved_stock=preorder_service.get_reserved_stock(),
        search=search,
    )


@product_bp.route("/add", methods=["GET", "POST"])
@role_required("admin")
def add_product() -> str:

    """Render and handle the add product form."""
    inventory_service = InventoryService()

    if request.method == "POST":
        try:
            name, code, category, price, quantity, description = _parse_product_form()
            inventory_service.add_product(
                name=name,
                code=code,
                category=category,
                price=price,
                quantity=quantity,
                description=description,
            )
            flash("Product added successfully.", "success")
            return redirect(url_for("products.list_products"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("add_product.html")


@product_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_product(product_id: int) -> str:

    """Render and handle the edit product form."""
    inventory_service = InventoryService()
    product = inventory_service.get_product_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("products.list_products"))

    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "").strip()
            price = float(request.form.get("price", "0"))
            quantity = int(request.form.get("quantity", "0"))
            description = request.form.get("description", "").strip()

            inventory_service.update_product(
                product_id=product_id,
                name=name,
                category=category,
                price=price,
                quantity=quantity,
                description=description,
            )
            flash("Product updated successfully.", "success")
            return redirect(url_for("products.list_products"))
        except ValueError as exc:
            flash(str(exc), "danger")

    return render_template("edit_product.html", product=product)


@product_bp.route("/<int:product_id>/delete", methods=["POST"])
@role_required("admin")
def delete_product(product_id: int):

    """Delete a product and redirect back to the list."""
    inventory_service = InventoryService()

    try:
        inventory_service.delete_product(product_id)
        flash("Product deleted successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("products.list_products"))


@product_bp.route("/<int:product_id>/stock", methods=["POST"])
@role_required("admin")
def add_stock(product_id: int):

    """Handle stock increment requests."""
    inventory_service = InventoryService()

    try:
        quantity = int(request.form.get("stock_quantity", "0"))
        inventory_service.add_stock(product_id, quantity)
        flash("Stock updated successfully.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")

    return redirect(url_for("products.list_products"))
