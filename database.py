import sqlite3
from contextlib import contextmanager
from datetime import datetime
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
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                payment_method TEXT NOT NULL,     -- 'upi' or 'binance'
                gateway_order_id TEXT,            -- Razorpay order_id or Binance prepayId
                status TEXT DEFAULT 'pending',    -- pending / paid / failed / cancelled
                created_at TEXT,
                paid_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT
            )
        """)


# ---------------- Users ----------------
def upsert_user(user_id, username, first_name):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (user_id, username, first_name, datetime.utcnow().isoformat()))


# ---------------- Products ----------------
def add_product(name, description, price_inr, price_usdt, image_url="", stock=100):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO products (name, description, price_inr, price_usdt, image_url, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, description, price_inr, price_usdt, image_url, stock))
        return cur.lastrowid


def get_active_products():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM products WHERE active=1 AND stock > 0").fetchall()
        return [dict(r) for r in rows]


def get_product(product_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return dict(row) if row else None


def decrement_stock(product_id, qty=1):
    with get_conn() as conn:
        conn.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, product_id))


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
        conn.execute("UPDATE orders SET gateway_order_id=? WHERE id=?", (gateway_order_id, order_id))


def mark_order_paid(gateway_order_id):
    """Returns the order row (dict) that was marked paid, or None if not found."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE gateway_order_id=?", (gateway_order_id,)).fetchone()
        if not row:
            return None
        conn.execute("""
            UPDATE orders SET status='paid', paid_at=? WHERE gateway_order_id=?
        """, (datetime.utcnow().isoformat(), gateway_order_id))
        return dict(row)


def get_order(order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_user_orders(user_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]
