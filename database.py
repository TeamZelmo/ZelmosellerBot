from contextlib import contextmanager
from datetime import datetime
import sqlite3
from config import DB_PATH[cite: 4, 5]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)[cite: 5]
    conn.row_factory = sqlite3.Row[cite: 5]
    try:
        yield conn[cite: 5]
        conn.commit()[cite: 5]
    finally:
        conn.close()[cite: 5]


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()[cite: 5]
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
        """)[cite: 5]
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
        """)[cite: 5]
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                currency TEXT DEFAULT 'INR',
                wallet_balance REAL DEFAULT 0.0,
                joined_at TEXT
            )
        """)[cite: 5]


# ---------------- Users ----------------
def upsert_user(user_id, username, first_name):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name, datetime.utcnow().isoformat()))[cite: 5]


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
def add_product(name, description, price_inr, price_usdt, image_url="", stock=100):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO products (name, description, price_inr, price_usdt, image_url, stock, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (name, description, price_inr, price_usdt, image_url, stock))[cite: 5]
        return cur.lastrowid[cite: 5]


def get_active_products():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM products WHERE active = 1 AND stock > 0").fetchall()[cite: 5]
        return [dict(r) for r in rows][cite: 5]


def get_product(product_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()[cite: 5]
        return dict(row) if row else None[cite: 5]


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


def decrement_stock(product_id, qty=1):
    with get_conn() as conn:
        conn.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?", (qty, product_id))[cite: 5]


# ---------------- Orders ----------------
def create_order(user_id, username, product_id, quantity, amount, currency, payment_method):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO orders (user_id, username, product_id, quantity, amount, currency,
                                 payment_method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (user_id, username, product_id, quantity, amount, currency,
              payment_method, datetime.utcnow().isoformat()))[cite: 5]
        return cur.lastrowid[cite: 5]


def set_gateway_order_id(order_id, gateway_order_id):
    with get_conn() as conn:
        conn.execute("UPDATE orders SET gateway_order_id = ? WHERE id = ?", (gateway_order_id, order_id))[cite: 5]


def mark_order_paid(gateway_order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE gateway_order_id = ?", (gateway_order_id,)).fetchone()[cite: 5]
        if not row:
            return None[cite: 5]
        conn.execute("""
            UPDATE orders SET status = 'paid', paid_at = ? WHERE gateway_order_id = ?
        """, (datetime.utcnow().isoformat(), gateway_order_id))[cite: 5]
        return dict(row)[cite: 5]


def get_order(order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()[cite: 5]
        return dict(row) if row else None[cite: 5]


def get_user_orders(user_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()[cite: 5]
        return [dict(r) for r in rows][cite: 5]
