"""Database connection and initialization helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "inventory.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection with row access by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database() -> None:
    """Create required database tables if they do not already exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff'
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                description TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                total_price REAL NOT NULL CHECK(total_price >= 0),
                sold_at TEXT NOT NULL,
                FOREIGN KEY (product_code) REFERENCES products(code)
                    ON UPDATE CASCADE ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS preorders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                status TEXT NOT NULL CHECK(status IN ('pending', 'delivered')),
                created_at TEXT NOT NULL,
                FOREIGN KEY (product_code) REFERENCES products(code)
                    ON UPDATE CASCADE ON DELETE RESTRICT
            );
            """
        )
        connection.commit()

