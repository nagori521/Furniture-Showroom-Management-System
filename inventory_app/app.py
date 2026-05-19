"""Flask application entry point for the showroom management app."""

from __future__ import annotations

from datetime import datetime

from flask import Flask, redirect, session, url_for

from config import Config
from database.db import initialize_database
from routes.auth_routes import auth_bp
from routes.customer_routes import customer_bp
from routes.dashboard_routes import dashboard_bp
from routes.preorder_routes import preorder_bp
from routes.product_routes import product_bp
from routes.report_routes import report_bp
from routes.sales_routes import sales_bp
from routes.payment_routes import payment_bp
from routes.manufacturing_order_routes import manufacturing_orders_bp
from services.auth_service import AuthService
from services.admin_service import ensure_default_admin

from services.inventory_service import InventoryService


def seed_sample_data() -> None:
    """Insert a small demo-ready product catalog only when data is missing."""
    inventory_service = InventoryService()

    if not inventory_service.list_products():
        sample_products = [
            {
                "name": "Classic Steel Almirah",
                "code": "ALM-ST-101",
                "category": "Steel Almirah",
                "price": 18990.00,
                "quantity": 6,
                "description": "Two-door powder-coated steel almirah with locker, shelves, and premium handle set.",
            },
            {
                "name": "Royal Wooden Wardrobe",
                "code": "WRD-WD-201",
                "category": "Wooden Wardrobe",
                "price": 36450.00,
                "quantity": 3,
                "description": "Wood-finish wardrobe with hanging space, drawers, and soft-close storage.",
            },
            {
                "name": "Sliding Door Wardrobe",
                "code": "WRD-SL-301",
                "category": "Wardrobe",
                "price": 42990.00,
                "quantity": 2,
                "description": "Premium sliding wardrobe for modern bedrooms with shelves and hanger section.",
            },
        ]

        for product in sample_products:
            inventory_service.add_product(**product)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    initialize_database()
    ensure_default_admin()
    from services.admin_service import ensure_default_staff
    ensure_default_staff()

    seed_sample_data()



    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(preorder_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(manufacturing_orders_bp)

    @app.route("/home")
    def home_redirect():
        """Redirect users based on authentication status."""
        if session.get("admin_id"):
            return redirect(url_for("dashboard.dashboard"))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_admin():
        """Expose current admin data to templates."""
        admin = None
        admin_id = session.get("admin_id")
        if admin_id:
            admin = AuthService().get_admin_by_id(int(admin_id))
        return {
            "current_admin": admin,
            "shop_name": Config.SHOP_NAME,
            "shop_phone": Config.SHOP_PHONE,
            "shop_address": Config.SHOP_ADDRESS,
            "current_year": datetime.now().year,
        }

    @app.template_filter("datetime_display")
    def datetime_display(value: str) -> str:
        """Render ISO timestamps cleanly in templates."""
        return value.replace("T", " ")[:19] if value else ""

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5000)
