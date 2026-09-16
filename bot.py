import asyncio
from html import escape
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import config[cite: 3]
import database as db[cite: 3]
from keyboards import (
    check_payment_keyboard,
    currency_bottom_keyboard,
    main_bottom_keyboard,
    payment_method_keyboard,
    product_detail_keyboard,
    products_keyboard,
    profile_popup_keyboard,
)
from payments import binance_pay, razorpay_upi[cite: 3]

logging.basicConfig(level=logging.INFO)[cite: 3]
logger = logging.getLogger(__name__)[cite: 3]

bot = Bot(token=config.BOT_TOKEN)[cite: 3]
dp = Dispatcher()[cite: 3]


# ------------------------------------------------------------------
# /start & Main Navigation
# ------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)[cite: 3]
    user_name = escape(message.from_user.first_name or "Grahak")
    curr = db.get_user_currency(message.from_user.id)

    text = (
        f"👋 Namaste <b>{user_name}</b>!\n\n"
        "Hamare store mein aapka swagat hai. Neeche diye gaye buttons se navigate karein.\n\n"
        f"⚙️ Currency: <b>{curr}</b>"
    )
    await message.answer(text, reply_markup=main_bottom_keyboard(), parse_mode=ParseMode.HTML)
    await show_catalog(message)


async def show_catalog(message: Message):
    products = db.get_active_products()[cite: 3]
    if not products:
        await message.answer("Abhi koi product available nahi hai. Baad mein try karein.")[cite: 3]
        return
    curr = db.get_user_currency(message.from_user.id)
    await message.answer("🛍️ Hamare Products:", reply_markup=products_keyboard(products, curr))


@dp.message(F.text == "🛍️ Shop")
@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    await show_catalog(message)


@dp.message(F.text == "📦 Orders")
@dp.message(Command("orders"))
async def cmd_orders(message: Message):
    orders = db.get_user_orders(message.from_user.id)[cite: 3]
    if not orders:
        await message.answer("Aapka koi order nahi hai abhi tak.")[cite: 3]
        return
    lines = []
    for o in orders[:10]:
        product = db.get_product(o["product_id"])[cite: 3]
        pname = escape(product["name"]) if product else "Unknown"
        lines.append(
            f"#{o['id']} — {pname} x{o['quantity']} — "
            f"{o['amount']} {o['currency']} — <b>{o['status'].upper()}</b>"
        )
    await message.answer("📦 <b>Aapke Orders:</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# Profile Pop-up Handlers
# ------------------------------------------------------------------
@dp.message(F.text.in_(["👤 Profile", "profile"]))
async def handle_profile(message: Message):
    await message.answer(
        "Neeche button par click karke apni profile pop-up window mein dekhein:",
        reply_markup=profile_popup_keyboard()
    )


@dp.callback_query(F.data == "show_profile_popup")
async def show_profile_popup_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_profile(user_id)
    curr = db.get_user_currency(user_id)

    name = callback.from_user.first_name or "N/A"
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Not Set"
    balance = user_data.get("wallet_balance", 0.0) if user_data else 0.0

    popup_text = (
        f"👤 USER PROFILE\n\n"
        f"📛 Name: {name}\n"
        f"🆔 ID: {user_id}\n"
        f"🔗 Username: {username}\n"
        f"💰 Wallet: {balance:.2f} {curr}"
    )
    # show_alert=True screen par center pop-up dialog box open karta hai
    await callback.answer(popup_text, show_alert=True)


# ------------------------------------------------------------------
# Support Handler
# ------------------------------------------------------------------
@dp.message(F.text.in_(["💬 Support", "support"]))
async def handle_support(message: Message):
    admin_contact = f"tg://user?id={config.ADMIN_IDS[0]}" if config.ADMIN_IDS else "Admin"
    await message.answer(
        "Agar aapko koi query ya problem hai toh support se contact karein:\n\n"
        f"👨‍💻 Support Admin: <a href='{admin_contact}'>Contact Here</a>",
        parse_mode=ParseMode.HTML
    )


# ------------------------------------------------------------------
# Currency Settings
# ------------------------------------------------------------------
@dp.message(F.text == "💱 Change Currency")
async def ask_currency(message: Message):
    current = db.get_user_currency(message.from_user.id)
    await message.answer(
        f"Apni preferred currency choose karein.\n\nAbhi select hai: <b>{current}</b>",
        reply_markup=currency_bottom_keyboard(),
        parse_mode=ParseMode.HTML,
    )


@dp.message(F.text.in_(["🇮🇳 INR (₹)", "🪙 USDT ($)"]))
async def set_currency(message: Message):
    new_curr = "INR" if "INR" in message.text else "USDT"
    db.set_user_currency(message.from_user.id, new_curr)
    await message.answer(
        f"✅ Aapki currency badal kar <b>{new_curr}</b> kar di gayi hai!",
        reply_markup=main_bottom_keyboard(),
        parse_mode=ParseMode.HTML,
    )


@dp.message(F.text == "🔙 Back to Menu")
async def back_menu(message: Message):
    await message.answer("Main menu par wapas aa gaye:", reply_markup=main_bottom_keyboard())


# ------------------------------------------------------------------
# Admin Commands
# ------------------------------------------------------------------
@dp.message(Command("addproduct"))
async def cmd_add_product(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:[cite: 3]
        await message.answer("⛔ Aap admin nahi hain.")[cite: 3]
        return[cite: 3]
    try:
        raw = message.text.split(" ", 1)[1][cite: 3]
        name, desc, price_inr, price_usdt, stock = [x.strip() for x in raw.split("|")][cite: 3]
        pid = db.add_product(name, desc, float(price_inr), float(price_usdt), stock=int(stock))[cite: 3]
        await message.answer(f"✅ Product added with ID <code>{pid}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(
            "❌ Format galat hai. Use:\n"
            "<code>/addproduct Name | Description | price_inr | price_usdt | stock</code>\n\n"
            f"Error: {escape(str(e))}",
            parse_mode=ParseMode.HTML,
        )


@dp.message(Command("delproduct"))
async def cmd_del_product(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Format: <code>/delproduct &lt;id&gt;</code>", parse_mode=ParseMode.HTML)
            return
        product_id = int(parts[1])
        if db.delete_product(product_id):
            await message.answer(f"🗑️ Product ID <code>{product_id}</code> successfully hata diya gaya.", parse_mode=ParseMode.HTML)
        else:
            await message.answer(f"❌ Product ID <code>{product_id}</code> nahi mila.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}", parse_mode=ParseMode.HTML)


@dp.message(Command("setprice"))
async def cmd_set_price(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split(" ", 1)
        product_id, price_inr, price_usdt = [x.strip() for x in parts[1].split("|")]
        if db.update_product_price(int(product_id), float(price_inr), float(price_usdt)):
            await message.answer(
                f"✅ Price updated for Product <code>{product_id}</code>: ₹{price_inr} | {price_usdt} USDT",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.answer(f"❌ Product ID <code>{product_id}</code> nahi mila.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(
            "❌ Format galat hai. Use:\n<code>/setprice &lt;id&gt; | &lt;price_inr&gt; | &lt;price_usdt&gt;</code>",
            parse_mode=ParseMode.HTML,
        )


@dp.message(Command("bulkadd"))
async def cmd_bulk_add(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split("\n", 1)
        if len(parts) < 2:
            await message.answer(
                "❌ Format: <code>/bulkadd\\nName | Desc | inr | usdt | stock</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        lines = [line.strip() for line in parts[1].strip().split("\n") if line.strip()]
        added = []
        for line in lines:
            name, desc, price_inr, price_usdt, stock = [x.strip() for x in line.split("|")]
            pid = db.add_product(name, desc, float(price_inr), float(price_usdt), stock=int(stock))
            added.append(f"• ID <code>{pid}</code>: {escape(name)}")

        await message.answer("✅ <b>Products Added:</b>\n\n" + "\n".join(added), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}", parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# Product Detail View
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])[cite: 3]
    product = db.get_product(product_id)[cite: 3]
    if not product:
        await callback.answer("Product nahi mila.", show_alert=True)[cite: 3]
        return[cite: 3]

    curr = db.get_user_currency(callback.from_user.id)
    price_tag = f"₹{product['price_inr']}" if curr == "INR" else f"{product['price_usdt']} USDT"

    text = (
        f"🛍️ <b>{escape(product['name'])}</b>\n\n"
        f"{escape(product['description'])}\n\n"
        f"💰 <b>Price:</b> {price_tag}\n"
        f"📦 <b>Stock:</b> {product['stock']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=product_detail_keyboard(product_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()[cite: 3]


@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery):
    products = db.get_active_products()[cite: 3]
    curr = db.get_user_currency(callback.from_user.id)
    await callback.message.edit_text("🛍️ Hamare Products:", reply_markup=products_keyboard(products, curr))
    await callback.answer()[cite: 3]


@dp.callback_query(F.data.startswith("buy_"))
async def choose_payment_method(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])[cite: 3]
    product = db.get_product(product_id)[cite: 3]
    if not product or product["stock"] <= 0:[cite: 3]
        await callback.answer("Yeh product out of stock hai.", show_alert=True)
        return[cite: 3]

    text = f"<b>{escape(product['name'])}</b> ke liye payment method choose karein:"
    await callback.message.edit_text(
        text,
        reply_markup=payment_method_keyboard(product_id),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()[cite: 3]


# ------------------------------------------------------------------
# Payment Gateways (UPI & Binance)
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("pay_upi_"))
async def pay_with_upi(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])[cite: 3]
    product = db.get_product(product_id)[cite: 3]
    if not product or product["stock"] <= 0:
        await callback.answer("Yeh product out of stock ho chuka hai.", show_alert=True)
        return

    order_id = db.create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        product_id=product_id,
        quantity=1,
        amount=product["price_inr"],
        currency="INR",
        payment_method="upi",
    )[cite: 3]

    try:
        link = razorpay_upi.create_upi_payment_link(
            order_db_id=order_id,
            amount_inr=product["price_inr"],
            description=product["name"],
            customer_name=callback.from_user.full_name,
            callback_url=f"{config.PUBLIC_BASE_URL}/webhook/razorpay",
        )[cite: 3]
        db.set_gateway_order_id(order_id, link["id"])[cite: 3]

        text = (
            f"💳 <b>UPI Payment</b>\n\n"
            f"Product: {escape(product['name'])}\n"
            f"Amount: ₹{product['price_inr']}\n\n"
            f"Neeche diye link par pay karein (GPay/PhonePe/Paytm):\n"
            f"{link['short_url']}\n\n"
            f"Payment ke baad neeche button dabayein."
        )
        await callback.message.edit_text(
            text,
            reply_markup=check_payment_keyboard(order_id),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        logger.exception("Razorpay error")[cite: 3]
        await callback.message.edit_text(f"❌ Payment error: {escape(str(e))}")
    await callback.answer()[cite: 3]


@dp.callback_query(F.data.startswith("pay_binance_"))
async def pay_with_binance(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])[cite: 3]
    product = db.get_product(product_id)[cite: 3]
    if not product or product["stock"] <= 0:
        await callback.answer("Yeh product out of stock ho chuka hai.", show_alert=True)
        return

    order_id = db.create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        product_id=product_id,
        quantity=1,
        amount=product["price_usdt"],
        currency="USDT",
        payment_method="binance",
    )[cite: 3]

    try:
        result = binance_pay.create_order(
            order_db_id=order_id,
            amount_usdt=product["price_usdt"],
            description=product["name"],
            goods_name=product["name"],
        )[cite: 3]
        if result.get("status") != "SUCCESS":[cite: 3]
            raise Exception(result.get("errorMessage", "Binance error"))[cite: 3]

        data = result["data"][cite: 3]
        db.set_gateway_order_id(order_id, data["prepayId"])[cite: 3]

        text = (
            f"🪙 <b>Binance Pay Payment</b>\n\n"
            f"Product: {escape(product['name'])}\n"
            f"Amount: {product['price_usdt']} USDT\n\n"
            f"Neeche diye link par pay karein Binance app se:\n"
            f"{data['checkoutUrl']}\n\n"
            f"Payment ke baad neeche button dabayein."
        )
        await callback.message.edit_text(
            text,
            reply_markup=check_payment_keyboard(order_id),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        logger.exception("Binance Pay error")[cite: 3]
        await callback.message.edit_text(f"❌ Payment error: {escape(str(e))}")
    await callback.answer()[cite: 3]


# ------------------------------------------------------------------
# Verification & Webhook Notifications
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("check_"))
async def check_status(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])[cite: 3]
    order = db.get_order(order_id)[cite: 3]
    if not order:
        await callback.answer("Order nahi mila.", show_alert=True)[cite: 3]
        return[cite: 3]

    if order["status"] == "paid":[cite: 3]
        product = db.get_product(order["product_id"])[cite: 3]
        pname = escape(product["name"]) if product else "Unknown"
        await callback.message.edit_text(
            f"✅ <b>Payment successful!</b>\n\n"
            f"Order #{order_id} — {pname}\n"
            f"Aapka order confirm ho gaya hai. Dhanyawad! 🙏",
            parse_mode=ParseMode.HTML,
        )
    else:
        await callback.answer("⏳ Payment abhi pending hai. Thodi der baad try karein.", show_alert=True)[cite: 3]


async def notify_payment_success(order: dict):
    product = db.get_product(order["product_id"])[cite: 3]
    pname = escape(product["name"]) if product else "Item"
    db.decrement_stock(order["product_id"], order["quantity"])[cite: 3]
    try:
        await bot.send_message(
            order["user_id"],
            f"✅ <b>Payment Received!</b>\n\n"
            f"Order #{order['id']} — {pname}\n"
            f"Amount: {order['amount']} {order['currency']}\n\n"
            f"Aapka order confirm ho gaya hai. Dhanyawad! 🙏",
            parse_mode=ParseMode.HTML,
        )[cite: 3]
    except Exception:
        logger.exception("Failed to notify user %s", order.get("user_id"))
