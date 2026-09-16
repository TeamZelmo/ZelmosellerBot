import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile

import config
import database as db
from keyboards import (
    products_keyboard, product_detail_keyboard,
    payment_method_keyboard, check_payment_keyboard
)
from payments import razorpay_upi, binance_pay

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    text = (
        f"👋 Namaste {message.from_user.first_name}!\n\n"
        "Hamare store mein aapka swagat hai. Neeche products dekhein aur order karein.\n\n"
        "Commands:\n"
        "/shop — Products dekhein\n"
        "/orders — Apne orders dekhein"
    )
    await message.answer(text)
    await show_catalog(message)


async def show_catalog(message: Message):
    products = db.get_active_products()
    if not products:
        await message.answer("Abhi koi product available nahi hai. Baad mein try karein.")
        return
    await message.answer("🛍️ Hamare Products:", reply_markup=products_keyboard(products))


@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    await show_catalog(message)


@dp.message(Command("orders"))
async def cmd_orders(message: Message):
    orders = db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("Aapka koi order nahi hai abhi tak.")
        return
    lines = []
    for o in orders[:10]:
        product = db.get_product(o["product_id"])
        pname = product["name"] if product else "Unknown"
        lines.append(
            f"#{o['id']} — {pname} x{o['quantity']} — "
            f"{o['amount']} {o['currency']} — {o['status'].upper()}"
        )
    await message.answer("📦 Aapke Orders:\n\n" + "\n".join(lines))


# ------------------------------------------------------------------
# Admin: quick add product (simple text command)
# /addproduct Name | Description | price_inr | price_usdt | stock
# ------------------------------------------------------------------
@dp.message(Command("addproduct"))
async def cmd_add_product(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        raw = message.text.split(" ", 1)[1]
        name, desc, price_inr, price_usdt, stock = [x.strip() for x in raw.split("|")]
        pid = db.add_product(name, desc, float(price_inr), float(price_usdt), stock=int(stock))
        await message.answer(f"✅ Product added with ID {pid}")
    except Exception as e:
        await message.answer(
            "❌ Format galat hai. Use:\n"
            "/addproduct Name | Description | price_inr | price_usdt | stock\n\n"
            f"Error: {e}"
        )


# ------------------------------------------------------------------
# Product detail view
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    if not product:
        await callback.answer("Product nahi mila.", show_alert=True)
        return

    text = (
        f"🛍️ *{product['name']}*\n\n"
        f"{product['description']}\n\n"
        f"💰 Price: ₹{product['price_inr']}  |  {product['price_usdt']} USDT\n"
        f"📦 Stock: {product['stock']}"
    )
    await callback.message.edit_text(text, reply_markup=product_detail_keyboard(product_id), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery):
    products = db.get_active_products()
    await callback.message.edit_text("🛍️ Hamare Products:", reply_markup=products_keyboard(products))
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def choose_payment_method(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    if not product or product["stock"] <= 0:
        await callback.answer("Yeh product abhi available nahi hai.", show_alert=True)
        return
    text = f"*{product['name']}* ke liye payment method choose karein:"
    await callback.message.edit_text(text, reply_markup=payment_method_keyboard(product_id), parse_mode="Markdown")
    await callback.answer()


# ------------------------------------------------------------------
# UPI Payment (Razorpay)
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("pay_upi_"))
async def pay_with_upi(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    product = db.get_product(product_id)
    if not product:
        await callback.answer("Product nahi mila.", show_alert=True)
        return

    order_id = db.create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        product_id=product_id,
        quantity=1,
        amount=product["price_inr"],
        currency="INR",
        payment_method="upi",
    )

    try:
        link = razorpay_upi.create_upi_payment_link(
            order_db_id=order_id,
            amount_inr=product["price_inr"],
            description=product["name"],
            customer_name=callback.from_user.full_name,
            callback_url=f"{config.PUBLIC_BASE_URL}/razorpay/callback",
        )
        db.set_gateway_order_id(order_id, link["id"])

        text = (
            f"💳 *UPI Payment*\n\n"
            f"Product: {product['name']}\n"
            f"Amount: ₹{product['price_inr']}\n\n"
            f"Neeche diye link par pay karein (GPay/PhonePe/Paytm sab chalega):\n"
            f"{link['short_url']}\n\n"
            f"Payment ke baad neeche button dabayein."
        )
        await callback.message.edit_text(
            text, reply_markup=check_payment_keyboard(order_id),
            parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.exception("Razorpay error")
        await callback.message.edit_text(f"❌ Payment link banane mein error aaya: {e}")
    await callback.answer()


# ------------------------------------------------------------------
# Binance Pay
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("pay_binance_"))
async def pay_with_binance(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    product = db.get_product(product_id)
    if not product:
        await callback.answer("Product nahi mila.", show_alert=True)
        return

    order_id = db.create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        product_id=product_id,
        quantity=1,
        amount=product["price_usdt"],
        currency="USDT",
        payment_method="binance",
    )

    try:
        result = binance_pay.create_order(
            order_db_id=order_id,
            amount_usdt=product["price_usdt"],
            description=product["name"],
            goods_name=product["name"],
        )
        if result.get("status") != "SUCCESS":
            raise Exception(result.get("errorMessage", "Unknown Binance error"))

        data = result["data"]
        prepay_id = data["prepayId"]
        checkout_url = data["checkoutUrl"]
        db.set_gateway_order_id(order_id, prepay_id)

        text = (
            f"🪙 *Binance Pay Payment*\n\n"
            f"Product: {product['name']}\n"
            f"Amount: {product['price_usdt']} USDT\n\n"
            f"Neeche diye link par pay karein Binance app se:\n"
            f"{checkout_url}\n\n"
            f"Payment ke baad neeche button dabayein."
        )
        await callback.message.edit_text(
            text, reply_markup=check_payment_keyboard(order_id),
            parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.exception("Binance Pay error")
        await callback.message.edit_text(f"❌ Payment link banane mein error aaya: {e}")
    await callback.answer()


# ------------------------------------------------------------------
# Check payment status (manual trigger; webhook auto-updates DB in background)
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("check_"))
async def check_status(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Order nahi mila.", show_alert=True)
        return

    if order["status"] == "paid":
        product = db.get_product(order["product_id"])
        await callback.message.edit_text(
            f"✅ Payment successful!\n\n"
            f"Order #{order_id} — {product['name']}\n"
            f"Aapka order confirm ho gaya hai. Dhanyawad! 🙏"
        )
    else:
        await callback.answer("⏳ Payment abhi pending hai. Thodi der baad try karein.", show_alert=True)


# ------------------------------------------------------------------
# This function is called by webhook_server.py when a payment succeeds,
# so the bot can proactively message the user.
# ------------------------------------------------------------------
async def notify_payment_success(order: dict):
    product = db.get_product(order["product_id"])
    db.decrement_stock(order["product_id"], order["quantity"])
    try:
        await bot.send_message(
            order["user_id"],
            f"✅ *Payment Received!*\n\n"
            f"Order #{order['id']} — {product['name']}\n"
            f"Amount: {order['amount']} {order['currency']}\n\n"
            f"Aapka order confirm ho gaya hai. Dhanyawad! 🙏",
            parse_mode="Markdown"
        )
    except Exception:
        logger.exception("Failed to notify user")


async def main():
    db.init_db()
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
