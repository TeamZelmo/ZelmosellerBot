from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------- Persistent Main Menu ----------------
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


# ---------------- Product Screen Bottom Buttons ----------------
def product_action_bottom_keyboard(product_id: int) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text=f"🛒 Buy Product #{product_id}")],
        [KeyboardButton(text="🔙 Back to Catalog"), KeyboardButton(text="🔙 Back to Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def payment_method_bottom_keyboard(product_id: int) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text=f"💳 Pay UPI #{product_id}"), KeyboardButton(text=f"🪙 Pay Binance #{product_id}")],
        [KeyboardButton(text="🔙 Back to Catalog"), KeyboardButton(text="🔙 Back to Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ---------------- Catalog Listing & Popups ----------------
def products_keyboard(products: list, currency: str = "INR") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        price = f"₹{p['price_inr']}" if currency == "INR" else f"{p['price_usdt']} USDT"
        kb.button(text=f"{p['name']} — {price}", callback_data=f"product_{p['id']}")
    kb.adjust(1)
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
