from contextlib import contextmanager
from datetime import datetime
import sqlite3
from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price_inr REAL NOT NULL,
                price_usdt REAL NOT NULL,
                image_url TEXT,
                stock INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                account_data TEXT NOT NULL,
                is_delivered INTEGER DEFAULT 0,
                order_id INTEGER,
                delivered_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                gateway_order_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                paid_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                currency TEXT DEFAULT 'INR',
                wallet_balance REAL DEFAULT 0.0,
                joined_at TEXT
            )
        """)


# ---------------- Users ----------------
def upsert_user(user_id, username, first_name):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name, datetime.utcnow().isoformat()))


def get_user_profile(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            data = dict(row)
            data.setdefault("wallet_balance", 0.0)
            return data
        return None


def set_user_currency(user_id: int, currency: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET currency = ? WHERE user_id = ?", (currency.upper(), user_id))


def get_user_currency(user_id: int) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT currency FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["currency"] if row and row["currency"] else "INR"


# ---------------- Products ----------------
def add_product(name, description, price_inr, price_usdt, image_url="", stock=0):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO products (name, description, price_inr, price_usdt, image_url, stock, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (name, description, price_inr, price_usdt, image_url, stock))
        return cur.lastrowid


def get_active_products():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM products WHERE active = 1 AND stock > 0").fetchall()
        return [dict(r) for r in rows]


def get_product(product_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None


def update_product_price(product_id: int, price_inr: float, price_usdt: float) -> bool:
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE products SET price_inr = ?, price_usdt = ? WHERE id = ?
        """, (price_inr, price_usdt, product_id))
        return cur.rowcount > 0


def delete_product(product_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
        return cur.rowcount > 0


# ---------------- Digital Accounts Storage & Bulk Delivery ----------------
def add_bulk_accounts(product_id: int, accounts_list: list) -> int:
    with get_conn() as conn:
        added = 0
        for acc in accounts_list:
            acc = acc.strip()
            if acc:
                conn.execute("""
                    INSERT INTO product_accounts (product_id, account_data, is_delivered)
                    VALUES (?, ?, 0)
                """, (product_id, acc))
                added += 1

        conn.execute("""
            UPDATE products 
            SET stock = (SELECT COUNT(*) FROM product_accounts WHERE product_id = ? AND is_delivered = 0)
            WHERE id = ?
        """, (product_id, product_id))
        return added


def deliver_accounts_for_order(product_id: int, order_id: int, quantity: int) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT id, account_data FROM product_accounts 
            WHERE product_id = ? AND is_delivered = 0 
            LIMIT ?
        """, (product_id, quantity)).fetchall()

        if not rows:
            return []

        delivered_accounts = []
        for r in rows:
            conn.execute("""
                UPDATE product_accounts 
                SET is_delivered = 1, order_id = ?, delivered_at = ?
                WHERE id = ?
            """, (order_id, datetime.utcnow().isoformat(), r["id"]))
            delivered_accounts.append(r["account_data"])

        conn.execute("""
            UPDATE products 
            SET stock = (SELECT COUNT(*) FROM product_accounts WHERE product_id = ? AND is_delivered = 0)
            WHERE id = ?
        """, (product_id, product_id))

        return delivered_accounts


# ---------------- Orders ----------------
def create_order(user_id, username, product_id, quantity, amount, currency, payment_method):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO orders (user_id, username, product_id, quantity, amount, currency,
                                 payment_method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (user_id, username, product_id, quantity, amount, currency,
              payment_method, datetime.utcnow().isoformat()))
        return cur.lastrowid


def set_gateway_order_id(order_id, gateway_order_id):
    with get_conn() as conn:
        conn.execute("UPDATE orders SET gateway_order_id = ? WHERE id = ?", (gateway_order_id, order_id))


def mark_order_paid(gateway_order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE gateway_order_id = ?", (gateway_order_id,)).fetchone()
        if not row:
            return None
        conn.execute("""
            UPDATE orders SET status = 'paid', paid_at = ? WHERE gateway_order_id = ?
        """, (datetime.utcnow().isoformat(), gateway_order_id))
        return dict(row)


def get_order(order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_user_orders(user_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]
