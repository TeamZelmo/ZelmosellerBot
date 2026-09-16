from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def products_keyboard(products: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=f"{p['name']} — ₹{p['price_inr']}", callback_data=f"product_{p['id']}")
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
    kb.button(text="💳 Pay with UPI", callback_data=f"pay_upi_{product_id}")
    kb.button(text="🪙 Pay with Binance (USDT)", callback_data=f"pay_binance_{product_id}")
    kb.button(text="⬅️ Cancel", callback_data="back_to_catalog")
    kb.adjust(1)
    return kb.as_markup()


def check_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ I've Paid — Check Status", callback_data=f"check_{order_id}")
    kb.adjust(1)
    return kb.as_markup()
