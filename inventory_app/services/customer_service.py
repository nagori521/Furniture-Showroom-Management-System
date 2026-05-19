"""Customer service for CRUD and lookup workflows."""

from __future__ import annotations

import sqlite3

from database.db import get_connection
from database.models import Customer, utc_now_iso


class CustomerService:
    """Encapsulates customer operations."""

    DEFAULT_WALK_IN_PHONE = "0000000000"

    def add_customer(self, name: str, phone: str, address: str) -> Customer:
        """Create a new customer."""
        normalized_phone = self._normalize_phone(phone)
        self._validate_customer(name, normalized_phone, address)
        existing = self.find_by_phone(normalized_phone)
        if existing and normalized_phone != self.DEFAULT_WALK_IN_PHONE:
            raise ValueError(
                "A customer with this phone number already exists. "
                "Please select the existing customer."
            )

        try:
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO customers (name, phone, address, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name.strip(), normalized_phone, address.strip(), utc_now_iso()),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("Customer could not be created.") from exc

        return self.get_customer_by_id(int(cursor.lastrowid))

    def update_customer(self, customer_id: int, name: str, phone: str, address: str) -> Customer:
        """Update customer details."""
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        normalized_phone = self._normalize_phone(phone)
        self._validate_customer(name, normalized_phone, address)
        existing = self.find_by_phone(normalized_phone)
        if existing and existing.id != customer_id and normalized_phone != self.DEFAULT_WALK_IN_PHONE:
            raise ValueError("Another customer is already using this phone number.")

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE customers
                SET name = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (name.strip(), normalized_phone, address.strip(), customer_id),
            )
            connection.commit()

        return self.get_customer_by_id(customer_id)

    def delete_customer(self, customer_id: int) -> None:
        """Delete a customer when it is safe to do so."""
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        if customer.phone == self.DEFAULT_WALK_IN_PHONE and customer.name == "Walk-in Customer":
            raise ValueError("The default walk-in customer cannot be deleted.")

        try:
            with get_connection() as connection:
                connection.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Cannot delete a customer linked to sales or preorders."
            ) from exc

    def get_customer_by_id(self, customer_id: int) -> Customer | None:
        """Return a customer by ID."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM customers WHERE id = ?",
                (customer_id,),
            ).fetchone()
        return Customer.from_row(row) if row else None

    def list_customers(self, search: str | None = None) -> list[Customer]:
        """Return customers, optionally filtered by search text."""
        query = "SELECT * FROM customers"
        params: list[str] = []

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query += " WHERE name LIKE ? OR phone LIKE ? OR address LIKE ?"
            params.extend([pattern, pattern, pattern])

        query += " ORDER BY created_at DESC, name ASC"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Customer.from_row(row) for row in rows]

    def find_by_phone(self, phone: str) -> Customer | None:
        """Return the customer matching a phone number."""
        normalized_phone = self._normalize_phone(phone)
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM customers WHERE phone = ?",
                (normalized_phone,),
            ).fetchone()
        return Customer.from_row(row) if row else None

    def resolve_customer(
        self,
        customer_id: int | None = None,
        name: str = "",
        phone: str = "",
        address: str = "",
    ) -> Customer:
        """Return an existing customer or create a new one from form input."""
        if customer_id:
            customer = self.get_customer_by_id(customer_id)
            if not customer:
                raise ValueError("Selected customer was not found.")
            return customer

        if not any(value.strip() for value in (name, phone, address)):
            raise ValueError("Select an existing customer or add a new customer.")

        return self.add_customer(name, phone, address)

    @staticmethod
    def _validate_customer(name: str, phone: str, address: str) -> None:
        """Validate customer fields."""
        if not name.strip():
            raise ValueError("Customer name is required.")
        if not phone.strip():
            raise ValueError("Phone number is required.")
        if not phone.isdigit() or len(phone) < 10:
            raise ValueError("Phone number must be at least 10 digits.")
        if not address.strip():
            raise ValueError("Address is required.")

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Strip formatting while preserving digits only."""
        return "".join(character for character in phone.strip() if character.isdigit())
