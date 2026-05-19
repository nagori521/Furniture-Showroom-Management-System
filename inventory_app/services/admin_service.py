"""Admin/staff authentication service for the showroom app.

This file provides:
- password hashing/verification using werkzeug
- default admin creation (admin / admin123)
- admin/staff authentication

The app's database schema (inventory_app/database/db.py) stores staff/admin
users in the `admins` table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_connection


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Represents an authenticated admin/staff user."""

    id: int
    username: str
    role: str


def _get_admin_schema_has_role(connection: sqlite3.Connection) -> bool:
    """Return True if the admins table contains a role column."""
    cols = connection.execute("PRAGMA table_info(admins)").fetchall()
    return any(row["name"] == "role" for row in cols)


def create_admin(username: str, password: str, role: str = "staff") -> int:
    """Create a new admin/staff user.

    Notes:
    - If the underlying schema does not have a `role` column yet, this will
      fall back to inserting only username/password.
    """
    if not username or not username.strip():
        raise ValueError("username must be non-empty")
    if not password:
        raise ValueError("password must be non-empty")
    if not role or not role.strip():
        raise ValueError("role must be non-empty")

    username = username.strip()
    role = role.strip()
    password_hash = generate_password_hash(password)

    with get_connection() as connection:
        has_role = _get_admin_schema_has_role(connection)
        cursor = connection.cursor()

        if has_role:
            cursor.execute(
                """
                INSERT INTO admins (username, password, role)
                VALUES (?, ?, ?)
                """,
                (username, password_hash, role),
            )
        else:
            cursor.execute(
                """
                INSERT INTO admins (username, password)
                VALUES (?, ?)
                """,
                (username, password_hash),
            )

        connection.commit()
        return int(cursor.lastrowid)


def authenticate_admin(username: str, password: str) -> Optional[AuthenticatedUser]:
    """Authenticate an admin/staff user."""
    if not username or not username.strip() or not password:
        return None

    username = username.strip()

    with get_connection() as connection:
        has_role = _get_admin_schema_has_role(connection)

        if has_role:
            row = connection.execute(
                "SELECT id, username, password, role FROM admins WHERE username = ?",
                (username,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT id, username, password FROM admins WHERE username = ?",
                (username,),
            ).fetchone()

    if not row:
        return None

    stored_hash = row["password"] if "password" in row.keys() else row["password"]
    if not check_password_hash(stored_hash, password):
        return None

    role = row["role"] if "role" in row.keys() and row["role"] else "staff"
    return AuthenticatedUser(id=int(row["id"]), username=str(row["username"]), role=str(role))


def ensure_default_admin() -> None:
    """Ensure the default admin user exists on app startup."""
    with get_connection() as connection:
        # If schema lacks role, create it (migration) with default 'staff'.
        has_role = _get_admin_schema_has_role(connection)
        if not has_role:
            connection.execute("ALTER TABLE admins ADD COLUMN role TEXT NOT NULL DEFAULT 'staff'")
            connection.commit()

        row = connection.execute(
            "SELECT id FROM admins WHERE username = ?",
            ("admin",),
        ).fetchone()
        if row:
            return

    # Create default admin with role='admin'
    try:
        create_admin("admin", "admin123", role="admin")
    except sqlite3.IntegrityError:
        return


def ensure_default_staff() -> None:
    """Ensure default staff user exists on app startup."""
    try:
        create_admin("staff1", "staff123", role="staff")
    except sqlite3.IntegrityError:
        return



