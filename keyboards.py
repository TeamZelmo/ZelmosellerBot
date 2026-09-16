from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------- Persistent Bottom Keyboards ----------------
def main_bottom_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🛍️ Shop"), KeyboardButton(text="📦 Orders"), KeyboardButton(text="profile"),],
        [KeyboardButton(text="💱 Change Currency"),  KeyboardButton(text="support")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def currency_bottom_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="🇮🇳 INR (₹)"), KeyboardButton(text="🪙 USDT ($)")],
        [KeyboardButton(text="🔙 Back to Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ---------------- Inline Message Keyboards ----------------
def products_keyboard(products: list, currency: str = "INR") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        price = f"₹{p['price_inr']}" if currency == "INR" else f"{p['price_usdt']} USDT"
        kb.button(text=f"{p['name']} — {price}", callback_data=f"product_{p['id']}")
    kb.adjust(1)
    return kb.as_markup()


def product_detail_keyboard(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Buy Now", callback_data=f"buy_{product_id}")
    kb.button(text="⬅️ Back", callback_data="back_to_catalog")
    kb.adjust(1)
    return kb.as_markup()


def payment_method_keyboard(product_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Pay with UPI (INR)", callback_data=f"pay_upi_{product_id}")
    kb.button(text="🪙 Pay with Binance (USDT)", callback_data=f"pay_binance_{product_id}")
    kb.button(text="⬅️ Cancel", callback_data="back_to_catalog")
    kb.adjust(1)
    return kb.as_markup()


def check_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ I've Paid — Check Status", callback_data=f"check_{order_id}")
    kb.adjust(1)
    return kb.as_markup()
