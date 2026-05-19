"""Dataclasses used by the showroom management application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Row


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class Product:
    """Represents a furniture product in inventory."""

    id: int | None
    name: str
    code: str
    category: str
    price: float
    quantity: int
    description: str
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Product":
        """Build a product from a SQLite row."""
        return cls(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            category=row["category"],
            price=float(row["price"]),
            quantity=int(row["quantity"]),
            description=row["description"] or "",
            created_at=row["created_at"],
        )


@dataclass(slots=True)
class Customer:
    """Represents a showroom customer."""

    id: int | None
    name: str
    phone: str
    address: str
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Customer":
        """Build a customer from a SQLite row."""
        return cls(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            address=row["address"] or "",
            created_at=row["created_at"],
        )


@dataclass(slots=True)
class Admin:
    """Represents an admin user."""

    id: int | None
    username: str
    password: str

    @classmethod
    def from_row(cls, row: Row) -> "Admin":
        """Build an admin from a SQLite row."""
        return cls(
            id=row["id"],
            username=row["username"],
            password=row["password"],
        )


@dataclass(slots=True)
class Sale:
    """Represents a completed customer sale."""

    id: int | None
    product_id: int
    customer_id: int
    product_name: str
    product_code: str
    customer_name: str
    customer_phone: str
    customer_address: str
    quantity: int
    unit_price: float
    total_price: float
    final_amount: float
    discount_amount: float
    advance_paid: float
    pending_amount: float
    payment_status: str
    invoice_number: str
    sold_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Sale":
        """Build a sale from a SQLite row."""
        return cls(
            id=row["id"],
            product_id=int(row["product_id"]),
            customer_id=int(row["customer_id"]),
            product_name=row["product_name"],
            product_code=row["product_code"],
            customer_name=row["customer_name"],
            customer_phone=row["customer_phone"] or "",
            customer_address=row["customer_address"] or "",
            quantity=int(row["quantity"]),
            unit_price=float(row["unit_price"]),
            total_price=float(row["total_price"]),
            final_amount=float(row["final_amount"] or row["total_price"] or 0),
            discount_amount=float(row["discount_amount"] or 0),
            advance_paid=float(row["advance_paid"] or 0),
            pending_amount=float(row["pending_amount"] or 0),
            payment_status=row["payment_status"] or "Pending",
            invoice_number=row["invoice_number"],
            sold_at=row["sold_at"],
        )

    @property
    def subtotal(self) -> float:
        """Return the pre-discount line total."""
        return self.unit_price * self.quantity

    @property
    def final_total(self) -> float:
        """Return the final payable amount."""
        return self.final_amount

    @property
    def paid_amount(self) -> float:
        """Return the total amount collected for this sale."""
        return self.advance_paid


@dataclass(slots=True)
class PaymentHistory:
    """Represents one payment collected against a sale invoice."""

    id: int | None
    sale_id: int
    customer_id: int
    payment_amount: float
    payment_method: str
    payment_note: str
    payment_date: str
    created_at: str
    invoice_number: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    product_name: str = ""

    @classmethod
    def from_row(cls, row: Row) -> "PaymentHistory":
        """Build a payment history item from a SQLite row."""
        return cls(
            id=row["id"],
            sale_id=int(row["sale_id"]),
            customer_id=int(row["customer_id"]),
            payment_amount=float(row["payment_amount"] or 0),
            payment_method=row["payment_method"],
            payment_note=row["payment_note"] or "",
            payment_date=row["payment_date"],
            created_at=row["created_at"],
            invoice_number=row["invoice_number"] if "invoice_number" in row.keys() else "",
            customer_name=row["customer_name"] if "customer_name" in row.keys() else "",
            customer_phone=row["customer_phone"] if "customer_phone" in row.keys() else "",
            product_name=row["product_name"] if "product_name" in row.keys() else "",
        )


@dataclass(slots=True)
class Preorder:
    """Represents a customer preorder with delivery tracking."""

    id: int | None
    product_id: int
    customer_id: int
    product_name: str
    product_code: str
    unit_price: float
    customer_name: str
    customer_phone: str
    customer_address: str
    quantity: int
    discount_amount: float
    final_amount: float
    advance_paid: float
    pending_amount: float
    delivery_date: str
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Preorder":
        """Build a preorder from a SQLite row."""
        return cls(
            id=row["id"],
            product_id=int(row["product_id"]),
            customer_id=int(row["customer_id"]),
            product_name=row["product_name"],
            product_code=row["product_code"],
            unit_price=float(row["unit_price"]),
            customer_name=row["customer_name"],
            customer_phone=row["customer_phone"] or "",
            customer_address=row["customer_address"] or "",
            quantity=int(row["quantity"]),
            discount_amount=float(row["discount_amount"] or 0),
            final_amount=float(row["final_amount"] or 0),
            advance_paid=float(row["advance_paid"] or 0),
            pending_amount=float(row["pending_amount"] or 0),
            delivery_date=row["delivery_date"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @property
    def subtotal(self) -> float:
        """Return the pre-discount preorder amount."""
        return self.unit_price * self.quantity

    @property
    def final_total(self) -> float:
        """Return the preorder amount payable after discount."""
        return self.final_amount

    @property
    def pending_total(self) -> float:
        """Return the currently unpaid preorder balance."""
        return self.pending_amount
