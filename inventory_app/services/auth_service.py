"""Admin/staff authentication service."""

from __future__ import annotations

from werkzeug.security import check_password_hash

from database.db import get_connection
from database.models import Admin
from services.admin_service import AuthenticatedUser


class AuthService:

    """Handles admin/staff authentication verification."""

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        """Authenticate an admin/staff user.

        Uses werkzeug.security.check_password_hash against stored hashes.
        """
        if not username or not password:
            return None

        username = username.strip()
        if not username:
            return None

        with get_connection() as connection:
            # Select role if present (schema may or may not have role column)
            cols = connection.execute("PRAGMA table_info(admins)").fetchall()
            has_role = any(col["name"] == "role" for col in cols)

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
            # Keep generic failure message; no debug leakage of whether username exists.
            return None

        stored_hash = row["password"]
        if not stored_hash:
            return None

        # Password hash verification
        if not check_password_hash(stored_hash, password):
            return None

        role = "staff"
        if "role" in row.keys() and row["role"]:
            role = str(row["role"])

        return AuthenticatedUser(id=int(row["id"]), username=str(row["username"]), role=role)

    def get_admin_by_id(self, admin_id: int) -> Admin | None:
        """Return an admin by ID."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM admins WHERE id = ?",
                (admin_id,),
            ).fetchone()
        return Admin.from_row(row) if row else None

