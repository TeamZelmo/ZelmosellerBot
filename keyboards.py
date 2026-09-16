from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------- Persistent Bottom Keyboards ----------------
def main_bottom_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🛍️ Shop"), KeyboardButton(text="📦 Orders"), KeyboardButton(text="👤 Profile")],
        [KeyboardButton(text="💱 Change Currency"), KeyboardButton(text="💬 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def currency_bottom_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🇮🇳 INR (₹)"), KeyboardButton(text="🪙 USDT ($)")],
        [KeyboardButton(text="🔙 Back to Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def payment_method_bottom_keyboard(product_id: int, quantity: int) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text=f"💳 Pay UPI #{product_id} x{quantity}"), KeyboardButton(text=f"🪙 Pay Binance #{product_id} x{quantity}")],
        [KeyboardButton(text="🔙 Back to Catalog"), KeyboardButton(text="🔙 Back to Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ---------------- Inline Keyboards ----------------
def products_keyboard(products: list, currency: str = "INR") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        price = f"₹{p['price_inr']}" if currency == "INR" else f"{p['price_usdt']} USDT"
        kb.button(text=f"{p['name']} — {price}", callback_data=f"product_{p['id']}")
    kb.adjust(1)
    return kb.as_markup()


def quantity_inline_keyboard(product_id: int, qty: int, stock: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    # Row 1: - , Display, +
    kb.button(text="➖", callback_data=f"qty_dec_{product_id}_{qty}")
    kb.button(text=f"📦 {qty}", callback_data="qty_noop")
    kb.button(text="➕", callback_data=f"qty_inc_{product_id}_{qty}_{stock}")

    # Row 2: Proceed
    kb.button(text="💳 Proceed to Checkout", callback_data=f"qty_confirm_{product_id}_{qty}")

    # Row 3: Back
    kb.button(text="⬅️ Back to Catalog", callback_data="back_to_catalog")

    kb.adjust(3, 1, 1)
    return kb.as_markup()


def profile_popup_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Open Profile Details", callback_data="show_profile_popup")
    return kb.as_markup()


def check_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ I've Paid — Check Status", callback_data=f"check_{order_id}")
    kb.adjust(1)
    return kb.as_markup()
