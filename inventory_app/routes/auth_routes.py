"""Authentication routes for admin login and logout."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services.auth_service import AuthService


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> str:
    """Render and process the login form."""
    if session.get("admin_id"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = AuthService().authenticate(username, password)
        if admin:
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            # Role-aware session (admin/staff)
            session["role"] = getattr(admin, "role", "staff") or "staff"


            flash("Welcome back.", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Clear the admin session."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
