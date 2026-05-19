"""Authentication helpers and decorators."""

from __future__ import annotations

from functools import wraps

from flask import flash, redirect, session, url_for


def current_role() -> str | None:
    """Return the current user's role from session (admin/staff)."""
    return session.get("role")


def role_required(*roles: str):
    """TEMPORARY: Role restriction disabled.

    This app is currently being restored to a stable single-admin workflow.
    Any logged-in admin/staff session is allowed to access these routes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "admin_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            # Ignore role restrictions for now.
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator



def login_required(view_func):
    """Require an authenticated admin session for a route."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped_view

