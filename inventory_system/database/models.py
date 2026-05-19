"""Data models used across the inventory system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from sqlite3 import Row


@dataclass(slots=True)
class Product:
    """Represents a furniture item stored in inventory."""

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
        """Build a Product instance from a database row."""
        return cls(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            category=row["category"],
            price=row["price"],
            quantity=row["quantity"],
            description=row["description"] or "",
            created_at=row["created_at"],
        )

    @classmethod
    def new(
        cls,
        name: str,
        code: str,
        category: str,
        price: float,
        quantity: int,
        description: str,
    ) -> "Product":
        """Create a new Product with the current UTC timestamp."""
        return cls(
            id=None,
            name=name,
            code=code,
            category=category,
            price=price,
            quantity=quantity,
            description=description,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )


@dataclass(slots=True)
class Sale:
    """Represents a completed sale transaction."""

    id: int | None
    product_code: str
    quantity: int
    total_price: float
    sold_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Sale":
        """Build a Sale instance from a database row."""
        return cls(
            id=row["id"],
            product_code=row["product_code"],
            quantity=row["quantity"],
            total_price=row["total_price"],
            sold_at=row["sold_at"],
        )


@dataclass(slots=True)
class Preorder:
    """Represents a customer preorder."""

    id: int | None
    product_code: str
    customer_name: str
    quantity: int
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> "Preorder":
        """Build a Preorder instance from a database row."""
        return cls(
            id=row["id"],
            product_code=row["product_code"],
            customer_name=row["customer_name"],
            quantity=row["quantity"],
            status=row["status"],
            created_at=row["created_at"],
        )


# Roles base system code below 
@dataclass(slots=True)
class Admin:
    """Represents an admin or staff user."""

    id: int | None
    username: str
    password_hash: str
    role: str

    @classmethod
    def from_row(cls, row: Row) -> "Admin":
        """Build an Admin instance from database row."""
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
        )