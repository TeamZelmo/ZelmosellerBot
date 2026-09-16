import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Telegram ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# ---------- Database ----------
DB_PATH = os.getenv("DB_PATH", "shop.db")

# ---------- Razorpay (UPI) ----------
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

# ---------- Binance Pay ----------
BINANCE_PAY_API_KEY = os.getenv("BINANCE_PAY_API_KEY", "")
BINANCE_PAY_API_SECRET = os.getenv("BINANCE_PAY_API_SECRET", "")
BINANCE_PAY_BASE_URL = "https://bpay.binanceapi.com"

# ---------- Webhook server ----------
# Public HTTPS URL jahan Razorpay/Binance webhooks bhejenge
# Example: https://yourdomain.com
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
WEBHOOK_SERVER_PORT = int(os.getenv("WEBHOOK_SERVER_PORT", "8000"))

# Currency
CURRENCY = "INR"
