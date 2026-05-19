"""Command-line interface for the inventory management system."""

from __future__ import annotations

from reports.report_generator import ReportGenerator
from services.inventory_service import InventoryService
from services.preorder_service import PreorderService
from services.sales_service import SalesService
from utils.helpers import (
    format_currency,
    format_datetime,
    get_float_input,
    get_int_input,
    print_error,
    print_info,
    print_section,
    print_success,
)


class InventoryCLI:
    """Interactive CLI dashboard for managing furniture inventory."""

    def __init__(self) -> None:
        self.inventory_service = InventoryService()
        self.sales_service = SalesService()
        self.preorder_service = PreorderService()
        self.report_generator = ReportGenerator()

    def run(self) -> None:
        """Run the main application loop."""
        while True:
            self._display_dashboard()
            choice = input("\nSelect an option: ").strip()

            try:
                if choice == "1":
                    self._add_product()
                elif choice == "2":
                    self._view_products()
                elif choice == "3":
                    self._search_product()
                elif choice == "4":
                    self._update_product()
                elif choice == "5":
                    self._delete_product()
                elif choice == "6":
                    self._add_stock()
                elif choice == "7":
                    self._record_sale()
                elif choice == "8":
                    self._manage_preorders()
                elif choice == "9":
                    self._view_reports()
                elif choice == "10":
                    print_info("Goodbye.")
                    break
                else:
                    print_error("Invalid menu option. Please choose 1-10.")
            except Exception as exc:  # pragma: no cover
                print_error(str(exc))

    def _display_dashboard(self) -> None:
        """Display dashboard metrics and the main menu."""
        inventory_summary = self.inventory_service.summarize_inventory()
        total_sales = self.sales_service.get_total_revenue()
        low_stock_items = inventory_summary["low_stock_items"]

        print_section("Furniture Inventory Dashboard")
        print(f"Total inventory value: {format_currency(inventory_summary['inventory_value'])}")
        print(f"Total sales revenue : {format_currency(total_sales)}")
        print(f"Products in catalog : {inventory_summary['product_count']}")

        if low_stock_items:
            print("Low stock alerts     :")
            for product in low_stock_items:
                print(
                    f"  - {product.name} ({product.code}) has only "
                    f"{product.quantity} unit(s) left"
                )
        else:
            print("Low stock alerts     : None")

        print(
            "\n1. Add Product\n"
            "2. View Products\n"
            "3. Search Product\n"
            "4. Update Product\n"
            "5. Delete Product\n"
            "6. Add Stock\n"
            "7. Record Sale\n"
            "8. Manage Preorders\n"
            "9. View Reports\n"
            "10. Exit"
        )

    def _add_product(self) -> None:
        """Prompt for and add a new product."""
        print_section("Add Product")
        name = input("Product name: ")
        code = input("Product code: ")
        category = input("Category (e.g. Steel Almirah): ")
        price = get_float_input("Price: ")
        quantity = get_int_input("Opening quantity: ")
        description = input("Description: ")

        product = self.inventory_service.add_product(
            name=name,
            code=code,
            category=category,
            price=price,
            quantity=quantity,
            description=description,
        )
        print_success(f"Product '{product.name}' added successfully.")

    def _view_products(self) -> None:
        """Show all products in inventory."""
        print_section("Product List")
        products = self.inventory_service.list_products()
        reserved = self.preorder_service.get_reserved_stock()

        if not products:
            print_info("No products found.")
            return

        for product in products:
            reserved_qty = reserved.get(product.code, 0)
            print(
                f"[{product.code}] {product.name} | {product.category} | "
                f"Price: {format_currency(product.price)} | "
                f"Available: {product.quantity} | Reserved: {reserved_qty}"
            )
            print(f"    Description: {product.description or 'N/A'}")
            print(f"    Created at : {format_datetime(product.created_at)}")

    def _search_product(self) -> None:
        """Search for products by keyword or code."""
        print_section("Search Product")
        query = input("Enter product name, code, or category: ")
        products = self.inventory_service.search_products(query)

        if not products:
            print_info("No matching products found.")
            return

        for product in products:
            print(
                f"[{product.code}] {product.name} | {product.category} | "
                f"{format_currency(product.price)} | Qty: {product.quantity}"
            )

    def _update_product(self) -> None:
        """Update an existing product."""
        print_section("Update Product")
        code = input("Enter product code: ").strip().upper()
        product = self.inventory_service.get_product_by_code(code)
        if not product:
            raise ValueError(f"Product with code '{code}' was not found.")

        print_info("Press Enter to keep the current value.")
        name = input(f"Name [{product.name}]: ").strip()
        category = input(f"Category [{product.category}]: ").strip()
        price_input = input(f"Price [{product.price}]: ").strip()
        quantity_input = input(f"Quantity [{product.quantity}]: ").strip()
        description = input(f"Description [{product.description}]: ")

        updated_product = self.inventory_service.update_product(
            code=code,
            name=name or None,
            category=category or None,
            price=float(price_input) if price_input else None,
            quantity=int(quantity_input) if quantity_input else None,
            description=description if description else None,
        )
        print_success(f"Product '{updated_product.code}' updated successfully.")

    def _delete_product(self) -> None:
        """Delete a product after confirmation."""
        print_section("Delete Product")
        code = input("Enter product code: ").strip().upper()
        confirm = input(f"Are you sure you want to delete '{code}'? (y/n): ").strip()
        if confirm.lower() != "y":
            print_info("Deletion cancelled.")
            return

        self.inventory_service.delete_product(code)
        print_success(f"Product '{code}' deleted successfully.")

    def _add_stock(self) -> None:
        """Increase stock for a product."""
        print_section("Add Stock")
        code = input("Enter product code: ").strip().upper()
        quantity = get_int_input("Quantity to add: ")
        product = self.inventory_service.add_stock(code, quantity)
        print_success(
            f"Stock updated. '{product.code}' now has {product.quantity} unit(s)."
        )

    def _record_sale(self) -> None:
        """Record a sale transaction."""
        print_section("Record Sale")
        code = input("Enter product code: ").strip().upper()
        quantity = get_int_input("Quantity sold: ")
        sale = self.sales_service.record_sale(code, quantity)
        print_success(
            f"Sale recorded for '{sale.product_code}'. "
            f"Total amount: {format_currency(sale.total_price)}."
        )

    def _manage_preorders(self) -> None:
        """Display preorder submenu."""
        while True:
            print_section("Manage Preorders")
            print(
                "1. Create Preorder\n"
                "2. Update Preorder Status\n"
                "3. View Preorders\n"
                "4. Back to Main Menu"
            )
            choice = input("Select an option: ").strip()

            if choice == "1":
                self._create_preorder()
            elif choice == "2":
                self._update_preorder_status()
            elif choice == "3":
                self._view_preorders()
            elif choice == "4":
                break
            else:
                print_error("Invalid preorder menu option.")

    def _create_preorder(self) -> None:
        """Create a new preorder record."""
        code = input("Enter product code: ").strip().upper()
        customer_name = input("Customer name: ")
        quantity = get_int_input("Reserved quantity: ")
        preorder = self.preorder_service.create_preorder(code, customer_name, quantity)
        print_success(
            f"Preorder #{preorder.id} created for {preorder.customer_name}."
        )

    def _update_preorder_status(self) -> None:
        """Update the status of an existing preorder."""
        preorder_id = get_int_input("Preorder ID: ")
        status = input("New status (pending/delivered): ")
        preorder = self.preorder_service.update_preorder_status(preorder_id, status)
        print_success(
            f"Preorder #{preorder.id} status updated to '{preorder.status}'."
        )

    def _view_preorders(self) -> None:
        """Display preorder records."""
        preorders = self.preorder_service.list_preorders()
        if not preorders:
            print_info("No preorder records found.")
            return

        for preorder in preorders:
            print(
                f"#{preorder.id} | {preorder.customer_name} | "
                f"{preorder.product_code} | Qty: {preorder.quantity} | "
                f"Status: {preorder.status} | "
                f"Created: {format_datetime(preorder.created_at)}"
            )

    def _view_reports(self) -> None:
        """Display report submenu and generated outputs."""
        while True:
            print_section("Reports")
            print(
                "1. Sales Report\n"
                "2. Inventory Report\n"
                "3. Preorder Report\n"
                "4. Back to Main Menu"
            )
            choice = input("Select a report: ").strip()

            if choice == "1":
                start_date = input("Start date (YYYY-MM-DD, optional): ").strip() or None
                end_date = input("End date (YYYY-MM-DD, optional): ").strip() or None
                print(self.report_generator.generate_sales_report(start_date, end_date))
            elif choice == "2":
                print(self.report_generator.generate_inventory_report())
            elif choice == "3":
                print(self.report_generator.generate_preorder_report())
            elif choice == "4":
                break
            else:
                print_error("Invalid report menu option.")
