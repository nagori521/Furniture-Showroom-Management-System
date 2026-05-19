"""Admin and staff authentication service.

This module provides secure password hashing and authentication for users stored
in the `admins` table.

Roles are expected to be stored in the `role` column.
- Admins: typically `admin`
- Staff: typically `staff`

Note: Authorization / permissions should be handled by routes/services consuming
these functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from inventory_system.database.db import get_connection


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Represents an authenticated admin/staff user."""

    id: int
    username: str
    role: str


def create_admin(username: str, password: str, role: str = "staff") -> int:
    """Create a new admin/staff user.

    Args:
        username: Unique username.
        password: Plaintext password (will be hashed).
        role: Role name stored in the `role` column.

    Returns:
        The created user's id.

    Raises:
        ValueError: If username/password/role are empty.
        sqlite3.IntegrityError: If username already exists.
    """
    if not username or not username.strip():
        raise ValueError("username must be non-empty")
    if not password:
        raise ValueError("password must be non-empty")
    if not role or not role.strip():
        raise ValueError("role must be non-empty")

    password_hash = generate_password_hash(password)

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO admins (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username.strip(), password_hash, role.strip()),
        )
        connection.commit()
        return int(cursor.lastrowid)


def authenticate_admin(username: str, password: str) -> Optional[AuthenticatedUser]:
    """Authenticate an admin/staff user by username and password.

    Args:
        username: Username.
        password: Plaintext password.

    Returns:
        AuthenticatedUser if credentials are valid, otherwise None.
    """
    if not username or not username.strip() or not password:
        return None

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, username, password_hash, role
            FROM admins
            WHERE username = ?
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return AuthenticatedUser(id=int(row["id"]), username=str(row["username"]), role=str(row["role"]))

