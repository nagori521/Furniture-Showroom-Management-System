"""Database helpers for SQLite initialization, migrations, and connections."""

from __future__ import annotations

import sqlite3

from werkzeug.security import generate_password_hash

from config import Config
from database.models import utc_now_iso


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection configured for dict-like row access."""
    connection = sqlite3.connect(Config.DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database() -> None:
    """Create or migrate all required tables."""
    Config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        _create_core_tables(connection)
        _migrate_legacy_sales_table(connection)
        _migrate_legacy_preorders_table(connection)
        _create_payment_history_table(connection)
        _create_manufacturing_tables(connection)
        _seed_default_admin(connection)
        connection.commit()


def _create_core_tables(connection: sqlite3.Connection) -> None:
    """Create the latest table schema if not already present."""
    connection.executescript(
        """
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

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        """
    )


def _migrate_legacy_sales_table(connection: sqlite3.Connection) -> None:
    """Create or migrate the sales table to the current schema."""
    sales_exists = _table_exists(connection, "sales")

    if not sales_exists:
        connection.execute(
            """
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                total_price REAL NOT NULL CHECK(total_price >= 0),
                final_amount REAL NOT NULL DEFAULT 0 CHECK(final_amount >= 0),
                discount_amount REAL NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
                advance_paid REAL NOT NULL DEFAULT 0 CHECK(advance_paid >= 0),
                pending_amount REAL NOT NULL DEFAULT 0 CHECK(pending_amount >= 0),
                payment_status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK(payment_status IN ('Paid', 'Partial', 'Pending')),
                invoice_number TEXT NOT NULL UNIQUE,
                sold_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
                    ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
                    ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )
        connection.execute(
            """
            UPDATE sales
            SET payment_status = CASE
                WHEN COALESCE(pending_amount, 0) <= 0 THEN 'Paid'
                WHEN COALESCE(advance_paid, 0) > 0 THEN 'Partial'
                ELSE 'Pending'
            END
            """
        )
        return

    sale_columns = _get_columns(connection, "sales")
    if "discount_amount" not in sale_columns:
        connection.execute(
            """
            ALTER TABLE sales
            ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0
            CHECK(discount_amount >= 0)
            """
        )
        sale_columns = _get_columns(connection, "sales")

    if "final_amount" not in sale_columns:
        connection.execute(
            """
            ALTER TABLE sales
            ADD COLUMN final_amount REAL NOT NULL DEFAULT 0
            CHECK(final_amount >= 0)
            """
        )
        connection.execute(
            """
            UPDATE sales
            SET final_amount = COALESCE(total_price, 0)
            """
        )
        sale_columns = _get_columns(connection, "sales")

    if "advance_paid" not in sale_columns:
        connection.execute(
            """
            ALTER TABLE sales
            ADD COLUMN advance_paid REAL NOT NULL DEFAULT 0
            CHECK(advance_paid >= 0)
            """
        )
        sale_columns = _get_columns(connection, "sales")

    if "pending_amount" not in sale_columns:
        connection.execute(
            """
            ALTER TABLE sales
            ADD COLUMN pending_amount REAL NOT NULL DEFAULT 0
            CHECK(pending_amount >= 0)
            """
        )
        connection.execute(
            """
            UPDATE sales
            SET pending_amount = MAX(COALESCE(final_amount, 0) - COALESCE(advance_paid, 0), 0)
            """
        )
        sale_columns = _get_columns(connection, "sales")

    if "payment_status" not in sale_columns:
        connection.execute(
            """
            ALTER TABLE sales
            ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'Pending'
            CHECK(payment_status IN ('Paid', 'Partial', 'Pending'))
            """
        )
        sale_columns = _get_columns(connection, "sales")

    connection.execute(
        """
        UPDATE sales
        SET payment_status = CASE
            WHEN COALESCE(pending_amount, 0) <= 0 THEN 'Paid'
            WHEN COALESCE(advance_paid, 0) > 0 THEN 'Partial'
            ELSE 'Pending'
        END
        """
    )

    required = {
        "customer_id",
        "unit_price",
        "invoice_number",
        "discount_amount",
        "final_amount",
        "advance_paid",
        "pending_amount",
        "payment_status",
    }
    if required.issubset(sale_columns):
        return

    default_customer_id = _ensure_default_customer(connection)
    connection.execute("ALTER TABLE sales RENAME TO sales_legacy")
    connection.execute(
        """
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            total_price REAL NOT NULL CHECK(total_price >= 0),
            final_amount REAL NOT NULL DEFAULT 0 CHECK(final_amount >= 0),
            discount_amount REAL NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
            advance_paid REAL NOT NULL DEFAULT 0 CHECK(advance_paid >= 0),
            pending_amount REAL NOT NULL DEFAULT 0 CHECK(pending_amount >= 0),
            payment_status TEXT NOT NULL DEFAULT 'Pending'
                CHECK(payment_status IN ('Paid', 'Partial', 'Pending')),
            invoice_number TEXT NOT NULL UNIQUE,
            sold_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        )
        """
    )
    legacy_rows = connection.execute("SELECT * FROM sales_legacy ORDER BY id").fetchall()
    for row in legacy_rows:
        sold_at = row["sold_at"]
        invoice_number = f"INV-{row['id']:05d}"
        if "unit_price" in sale_columns:
            unit_price = float(row["unit_price"])
        else:
            quantity = max(int(row["quantity"]), 1)
            unit_price = float(row["total_price"]) / quantity
        customer_id = int(row["customer_id"]) if "customer_id" in sale_columns else default_customer_id
        discount_amount = float(row["discount_amount"]) if "discount_amount" in sale_columns else 0.0
        final_amount = float(row["final_amount"]) if "final_amount" in sale_columns else float(row["total_price"])
        advance_paid = float(row["advance_paid"]) if "advance_paid" in sale_columns else 0.0
        pending_amount = (
            float(row["pending_amount"])
            if "pending_amount" in sale_columns
            else max(final_amount - advance_paid, 0.0)
        )
        payment_status = _calculate_payment_status(advance_paid, pending_amount)
        connection.execute(
            """
            INSERT INTO sales (
                id, product_id, customer_id, quantity, unit_price,
                total_price, final_amount, discount_amount, advance_paid, pending_amount,
                invoice_number, sold_at, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["product_id"],
                customer_id,
                row["quantity"],
                unit_price,
                row["total_price"],
                final_amount,
                discount_amount,
                advance_paid,
                pending_amount,
                invoice_number,
                sold_at,
                payment_status,
            ),
        )
    connection.execute("DROP TABLE sales_legacy")


def _create_payment_history_table(connection: sqlite3.Connection) -> None:
    """Create the customer payment ledger table."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            payment_amount REAL NOT NULL CHECK(payment_amount > 0),
            payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'UPI', 'Bank Transfer')),
            payment_note TEXT,
            payment_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payment_history_sale_id
        ON payment_history(sale_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payment_history_customer_id
        ON payment_history(customer_id)
        """
    )
    connection.execute(
        """
        INSERT INTO payment_history (
            sale_id, customer_id, payment_amount, payment_method,
            payment_note, payment_date, created_at
        )
        SELECT
            sales.id,
            sales.customer_id,
            sales.advance_paid,
            'Cash',
            'Opening paid amount migrated from sale record.',
            date(sales.sold_at),
            sales.sold_at
        FROM sales
        WHERE sales.advance_paid > 0
          AND NOT EXISTS (
              SELECT 1
              FROM payment_history
              WHERE payment_history.sale_id = sales.id
          )
        """
    )


def _migrate_legacy_preorders_table(connection: sqlite3.Connection) -> None:
    """Create or migrate the preorders table to the current schema."""
    preorder_exists = _table_exists(connection, "preorders")
    if not preorder_exists:
        connection.execute(
            """
            CREATE TABLE preorders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                discount_amount REAL NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
                final_amount REAL NOT NULL DEFAULT 0 CHECK(final_amount >= 0),
                advance_paid REAL NOT NULL DEFAULT 0 CHECK(advance_paid >= 0),
                pending_amount REAL NOT NULL DEFAULT 0 CHECK(pending_amount >= 0),
                delivery_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending', 'delivered')),
                created_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
                    ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
                    ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )
        return

    preorder_columns = _get_columns(connection, "preorders")
    if "discount_amount" not in preorder_columns:
        connection.execute(
            """
            ALTER TABLE preorders
            ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0
            CHECK(discount_amount >= 0)
            """
        )
        preorder_columns = _get_columns(connection, "preorders")

    if "final_amount" not in preorder_columns:
        connection.execute(
            """
            ALTER TABLE preorders
            ADD COLUMN final_amount REAL NOT NULL DEFAULT 0
            CHECK(final_amount >= 0)
            """
        )
        connection.execute(
            """
            UPDATE preorders
            SET final_amount = MAX(
                (quantity * COALESCE(
                    (SELECT price FROM products WHERE products.id = preorders.product_id),
                    0
                )) - COALESCE(discount_amount, 0),
                0
            )
            """
        )
        preorder_columns = _get_columns(connection, "preorders")

    if "advance_paid" not in preorder_columns:
        connection.execute(
            """
            ALTER TABLE preorders
            ADD COLUMN advance_paid REAL NOT NULL DEFAULT 0
            CHECK(advance_paid >= 0)
            """
        )
        preorder_columns = _get_columns(connection, "preorders")

    if "pending_amount" not in preorder_columns:
        connection.execute(
            """
            ALTER TABLE preorders
            ADD COLUMN pending_amount REAL NOT NULL DEFAULT 0
            CHECK(pending_amount >= 0)
            """
        )
        connection.execute(
            """
            UPDATE preorders
            SET pending_amount = MAX(COALESCE(final_amount, 0) - COALESCE(advance_paid, 0), 0)
            """
        )
        preorder_columns = _get_columns(connection, "preorders")

    required = {
        "customer_id",
        "delivery_date",
        "discount_amount",
        "final_amount",
        "advance_paid",
        "pending_amount",
    }
    if required.issubset(preorder_columns):
        return

    connection.execute("ALTER TABLE preorders RENAME TO preorders_legacy")
    connection.execute(
        """
        CREATE TABLE preorders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            discount_amount REAL NOT NULL DEFAULT 0 CHECK(discount_amount >= 0),
            final_amount REAL NOT NULL DEFAULT 0 CHECK(final_amount >= 0),
            advance_paid REAL NOT NULL DEFAULT 0 CHECK(advance_paid >= 0),
            pending_amount REAL NOT NULL DEFAULT 0 CHECK(pending_amount >= 0),
            delivery_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'delivered')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        )
        """
    )
    legacy_rows = connection.execute(
        "SELECT * FROM preorders_legacy ORDER BY id"
    ).fetchall()
    for row in legacy_rows:
        customer_id = _ensure_customer_from_legacy_row(connection, row)
        delivery_date = row["created_at"][:10]
        quantity = int(row["quantity"])
        discount_amount = float(row["discount_amount"]) if "discount_amount" in preorder_columns else 0.0
        if "final_amount" in preorder_columns:
            final_amount = float(row["final_amount"])
        else:
            product_row = connection.execute(
                "SELECT price FROM products WHERE id = ?",
                (row["product_id"],),
            ).fetchone()
            unit_price = float(product_row["price"]) if product_row else 0.0
            final_amount = max((unit_price * quantity) - discount_amount, 0.0)
        advance_paid = float(row["advance_paid"]) if "advance_paid" in preorder_columns else 0.0
        pending_amount = (
            float(row["pending_amount"])
            if "pending_amount" in preorder_columns
            else max(final_amount - advance_paid, 0.0)
        )
        connection.execute(
            """
            INSERT INTO preorders (
                id, product_id, customer_id, quantity,
                discount_amount, final_amount, advance_paid, pending_amount,
                delivery_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["product_id"],
                customer_id,
                quantity,
                discount_amount,
                final_amount,
                advance_paid,
                pending_amount,
                delivery_date,
                row["status"],
                row["created_at"],
            ),
        )
    connection.execute("DROP TABLE preorders_legacy")


def _seed_default_admin(connection: sqlite3.Connection) -> None:
    """Ensure one default admin account exists."""
    row = connection.execute(
        "SELECT id FROM admins WHERE username = ?",
        ("admin",),
    ).fetchone()
    if row:
        return

    connection.execute(
        "INSERT INTO admins (username, password) VALUES (?, ?)",
        ("admin", generate_password_hash("admin123")),
    )


def _ensure_default_customer(connection: sqlite3.Connection) -> int:
    """Ensure the default walk-in customer exists and return its ID."""
    row = connection.execute(
        "SELECT id FROM customers WHERE phone = ?",
        ("0000000000",),
    ).fetchone()
    if row:
        return int(row["id"])

    cursor = connection.execute(
        """
        INSERT INTO customers (name, phone, address, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("Walk-in Customer", "0000000000", "Showroom Desk", utc_now_iso()),
    )
    return int(cursor.lastrowid)


def _ensure_customer_from_legacy_row(connection: sqlite3.Connection, row: sqlite3.Row) -> int:
    """Map legacy preorder customer_name values into the customers table."""
    name = (row["customer_name"] or "Walk-in Customer").strip()
    phone = "0000000000"
    existing = connection.execute(
        "SELECT id FROM customers WHERE name = ? AND phone = ?",
        (name, phone),
    ).fetchone()
    if existing:
        return int(existing["id"])

    cursor = connection.execute(
        """
        INSERT INTO customers (name, phone, address, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, phone, "Migrated record", utc_now_iso()),
    )
    return int(cursor.lastrowid)


def _calculate_payment_status(paid_amount: float, pending_amount: float) -> str:
    """Return the normalized payment status for a sale."""
    if pending_amount <= 0:
        return "Paid"
    if paid_amount > 0:
        return "Partial"
    return "Pending"


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Return True when a table exists."""
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Return a set of column names for the given table."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _create_manufacturing_tables(connection: sqlite3.Connection) -> None:
    """Create manufacturing order tables (orders, items, deliveries)."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS manufacturing_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'partial', 'completed')),
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS manufacturing_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturing_order_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            ordered_quantity INTEGER NOT NULL CHECK(ordered_quantity >= 0),
            received_quantity INTEGER NOT NULL DEFAULT 0 CHECK(received_quantity >= 0),
            pending_quantity INTEGER NOT NULL DEFAULT 0 CHECK(pending_quantity >= 0),
            FOREIGN KEY (manufacturing_order_id)
                REFERENCES manufacturing_orders(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (product_code)
                REFERENCES products(code)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_mo_items_mo_id
        ON manufacturing_order_items(manufacturing_order_id);

        CREATE INDEX IF NOT EXISTS idx_mo_items_product_code
        ON manufacturing_order_items(product_code);

        CREATE TABLE IF NOT EXISTS manufacturing_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturing_order_item_id INTEGER NOT NULL,
            delivered_quantity INTEGER NOT NULL CHECK(delivered_quantity >= 0),
            delivered_at TEXT NOT NULL,
            FOREIGN KEY (manufacturing_order_item_id)
                REFERENCES manufacturing_order_items(id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_mo_deliveries_item_id
        ON manufacturing_deliveries(manufacturing_order_item_id);
        """
    )
