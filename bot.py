import asyncio
from html import escape
import logging
import requests

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

import config
import database as db
import binance_pay
import razorpay_upi
from keyboards import (
    check_payment_keyboard,
    currency_bottom_keyboard,
    main_bottom_keyboard,
    payment_method_bottom_keyboard,
    products_keyboard,
    profile_popup_keyboard,
    quantity_bottom_keyboard,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# ------------------------------------------------------------------
# /start & Main Navigation
# ------------------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
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
    products = db.get_active_products()
    if not products:
        await message.answer("Abhi koi product available nahi hai. Baad mein try karein.")
        return
    curr = db.get_user_currency(message.from_user.id)
    await message.answer(
        "🛍️ <b>Hamare Products:</b>\nNeeche kisi product par click karein:",
        reply_markup=products_keyboard(products, curr),
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text.in_(["🛍️ Shop", "🔙 Back to Catalog"]))
@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    await show_catalog(message)


@dp.message(F.text == "📦 Orders")
@dp.message(Command("orders"))
async def cmd_orders(message: Message):
    orders = db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("Aapka koi order nahi hai abhi tak.")
        return
    lines = []
    for o in orders[:10]:
        product = db.get_product(o["product_id"])
        pname = escape(product["name"]) if product else "Unknown"
        lines.append(
            f"#{o['id']} — {pname} x{o['quantity']} — "
            f"{o['amount']} {o['currency']} — <b>{o['status'].upper()}</b>"
        )
    await message.answer("📦 <b>Aapke Orders:</b>\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# Help Commands
# ------------------------------------------------------------------
@dp.message(Command("help"))
async def cmd_user_help(message: Message):
    text = (
        "📖 <b>User Guide:</b>\n\n"
        "• <code>/shop</code> se products catalog open karein.\n"
        "• Product select karne ke baad screen ke **neeche wale buttons** (➖ aur ➕) se quantity adjust karein.\n"
        "• Quantity confirm karke payment method choose karein. Payment hone par account turant yahin deliver ho jayega."
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("adminhelp"))
async def cmd_admin_help(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return

    text = (
        "🛠️ <b>Admin Commands:</b>\n\n"
        "➕ <b>Product Add:</b>\n"
        "<code>/addproduct Name | Description | price_inr | price_usdt</code>\n\n"
        "📦 <b>Bulk Products Add:</b>\n"
        "<code>/bulkadd\n"
        "Item 1 | Desc | inr | usdt\n"
        "Item 2 | Desc | inr | usdt</code>\n\n"
        "📥 <b>Stock Upload (Accounts):</b>\n"
        "<code>/addstock &lt;id&gt;\nemail1:pass1\nemail2:pass2</code>\n\n"
        "🔄 <b>GitHub Sync:</b>\n"
        "<code>/syncgithub</code> (JSON files direct repo se sync karta hai)\n\n"
        "✏️ <code>/setprice &lt;id&gt; | &lt;inr&gt; | &lt;usdt&gt;</code>\n"
        "🗑️ <code>/delproduct &lt;id&gt;</code>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# Profile & Support
# ------------------------------------------------------------------
@dp.message(F.text.in_(["👤 Profile", "profile"]))
async def handle_profile(message: Message):
    await message.answer("Neeche button dabakar profile window open karein:", reply_markup=profile_popup_keyboard())


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
    await callback.answer(popup_text, show_alert=True)


@dp.message(F.text.in_(["💬 Support", "support"]))
async def handle_support(message: Message):
    admin_contact = f"tg://user?id={config.ADMIN_IDS[0]}" if config.ADMIN_IDS else "Admin"
    await message.answer(f"👨‍💻 Support Admin: <a href='{admin_contact}'>Contact Here</a>", parse_mode=ParseMode.HTML)


# ------------------------------------------------------------------
# Currency Settings
# ------------------------------------------------------------------
@dp.message(F.text == "💱 Change Currency")
async def ask_currency(message: Message):
    current = db.get_user_currency(message.from_user.id)
    await message.answer(f"Preferred currency choose karein. Abhi: <b>{current}</b>", reply_markup=currency_bottom_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text.in_(["🇮🇳 INR (₹)", "🪙 USDT ($)"]))
async def set_currency(message: Message):
    new_curr = "INR" if "INR" in message.text else "USDT"
    db.set_user_currency(message.from_user.id, new_curr)
    await message.answer(f"✅ Currency badal kar <b>{new_curr}</b> kar di gayi hai!", reply_markup=main_bottom_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text == "🔙 Back to Menu")
async def back_menu(message: Message):
    await message.answer("Main menu par wapas aa gaye:", reply_markup=main_bottom_keyboard())


# ------------------------------------------------------------------
# Admin Commands & GitHub Sync
# ------------------------------------------------------------------
@dp.message(Command("addproduct"))
async def cmd_add_product(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        raw = message.text.split(" ", 1)[1]
        name, desc, price_inr, price_usdt = [x.strip() for x in raw.split("|")]
        pid = db.add_product(name, desc, float(price_inr), float(price_usdt), stock=0)
        await message.answer(f"✅ Product created with ID <code>{pid}</code>. Accounts upload karne ke liye <code>/addstock {pid}</code> use karein.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer("❌ Format: <code>/addproduct Name | Desc | inr | usdt</code>", parse_mode=ParseMode.HTML)


@dp.message(Command("bulkadd"))
async def cmd_bulk_add(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split("\n", 1)
        if len(parts) < 2:
            await message.answer("❌ Format:\n<code>/bulkadd\nName | Desc | inr | usdt</code>", parse_mode=ParseMode.HTML)
            return

        lines = [line.strip() for line in parts[1].strip().split("\n") if line.strip()]
        added = []
        for line in lines:
            name, desc, price_inr, price_usdt = [x.strip() for x in line.split("|")]
            pid = db.add_product(name, desc, float(price_inr), float(price_usdt), stock=0)
            added.append(f"• ID <code>{pid}</code>: <b>{escape(name)}</b>")

        await message.answer("✅ <b>Products Created:</b>\n\n" + "\n".join(added), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}")


@dp.message(Command("addstock"))
async def cmd_add_stock(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split("\n", 1)
        product_id = int(parts[0].strip().split()[1])
        product = db.get_product(product_id)
        if not product:
            await message.answer("❌ Product nahi mila.")
            return

        accounts = [x.strip() for x in parts[1].strip().split("\n") if x.strip()]
        added = db.add_bulk_accounts(product_id, accounts)
        fresh_product = db.get_product(product_id)
        await message.answer(f"✅ Product <b>{escape(product['name'])}</b> me <code>{added}</code> accounts add hue. Total stock: <code>{fresh_product['stock']}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}")


@dp.message(Command("syncgithub"))
async def cmd_sync_github(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return

    status_msg = await message.answer("🔄 <i>GitHub se data fetch ho raha hai...</i>", parse_mode=ParseMode.HTML)
    try:
        prod_resp = requests.get(config.GITHUB_PRODUCTS_URL, timeout=10)
        synced_prods = db.sync_products_from_list(prod_resp.json()) if prod_resp.status_code == 200 else 0

        stock_resp = requests.get(config.GITHUB_STOCK_URL, timeout=10)
        synced_stock = db.sync_stock_from_list(stock_resp.json()) if stock_resp.status_code == 200 else 0

        await status_msg.edit_text(
            f"✅ <b>GitHub Sync Complete!</b>\n\n"
            f"📦 Products Synced: <code>{synced_prods}</code>\n"
            f"🔑 Accounts Added: <code>{synced_stock}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Sync Error: {escape(str(e))}")


@dp.message(Command("delproduct"))
async def cmd_del_product(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split()
        product_id = int(parts[1])
        if db.delete_product(product_id):
            await message.answer(f"🗑️ Product #{product_id} deleted.", parse_mode=ParseMode.HTML)
        else:
            await message.answer("❌ Product nahi mila.")
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}")


@dp.message(Command("setprice"))
async def cmd_set_price(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Aap admin nahi hain.")
        return
    try:
        parts = message.text.split(" ", 1)
        product_id, price_inr, price_usdt = [x.strip() for x in parts[1].split("|")]
        if db.update_product_price(int(product_id), float(price_inr), float(price_usdt)):
            await message.answer(f"✅ Price updated for Product #{product_id}!", parse_mode=ParseMode.HTML)
        else:
            await message.answer("❌ Product nahi mila.")
    except Exception as e:
        await message.answer(f"❌ Error: {escape(str(e))}")


# ------------------------------------------------------------------
# Catalog Click -> Opens Bottom Quantity Selector
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("product_"))
async def show_product_qty(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    if not product or product["stock"] <= 0:
        await callback.answer("Yeh product out of stock hai.", show_alert=True)
        return

    curr = db.get_user_currency(callback.from_user.id)
    price_tag = f"₹{product['price_inr']}" if curr == "INR" else f"{product['price_usdt']} USDT"
    initial_qty = 1
    total_val = round((product['price_inr'] if curr == 'INR' else product['price_usdt']) * initial_qty, 2)
    total_tag = f"₹{total_val}" if curr == "INR" else f"{total_val} USDT"

    text = (
        f"🛍️ <b>{escape(product['name'])}</b>\n\n"
        f"{escape(product['description'])}\n\n"
        f"💰 <b>Rate:</b> {price_tag} per account\n"
        f"📦 <b>Stock:</b> {product['stock']}\n\n"
        f"🔢 <b>Selected Quantity:</b> <code>{initial_qty}</code>\n"
        f"💵 <b>Total Amount:</b> <b>{total_tag}</b>\n\n"
        "👇 <i>Neeche diye gaye <b>➖ / ➕</b> buttons se quantity badhayein ya ghatayein:</i>"
    )
    # Screen ke neeche Reply Keyboard bhejein
    await callback.message.answer(
        text,
        reply_markup=quantity_bottom_keyboard(product_id, initial_qty),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# ------------------------------------------------------------------
# Bottom Keyboard Quantity Minus / Plus / Confirm Handlers
# ------------------------------------------------------------------
@dp.message(F.text.startswith("➖ Dec #"))
async def decrease_qty_bottom(message: Message):
    try:
        raw = message.text.replace("➖ Dec #", "")
        product_id_str, current_qty_str = raw.split("_")
        product_id = int(product_id_str)
        current_qty = int(current_qty_str)

        if current_qty <= 1:
            await message.answer("⚠️ Minimum quantity 1 honi chahiye.")
            return

        new_qty = current_qty - 1
        product = db.get_product(product_id)
        curr = db.get_user_currency(message.from_user.id)
        unit_price = product['price_inr'] if curr == 'INR' else product['price_usdt']
        total_str = f"₹{round(unit_price * new_qty, 2)}" if curr == 'INR' else f"{round(unit_price * new_qty, 2)} USDT"

        await message.answer(
            f"🛍️ <b>{escape(product['name'])}</b>\n"
            f"🔢 Quantity: <code>{new_qty}</code>\n"
            f"💵 Total: <b>{total_str}</b>\n\n"
            "Neeche buttons se aur change karein ya Confirm dabayein:",
            reply_markup=quantity_bottom_keyboard(product_id, new_qty),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


@dp.message(F.text.startswith("➕ Inc #"))
async def increase_qty_bottom(message: Message):
    try:
        raw = message.text.replace("➕ Inc #", "")
        product_id_str, current_qty_str = raw.split("_")
        product_id = int(product_id_str)
        current_qty = int(current_qty_str)

        product = db.get_product(product_id)
        if current_qty >= product["stock"]:
            await message.answer(f"⚠️ Stock limit reach! Sirf {product['stock']} accounts bache hain.")
            return

        new_qty = current_qty + 1
        curr = db.get_user_currency(message.from_user.id)
        unit_price = product['price_inr'] if curr == 'INR' else product['price_usdt']
        total_str = f"₹{round(unit_price * new_qty, 2)}" if curr == 'INR' else f"{round(unit_price * new_qty, 2)} USDT"

        await message.answer(
            f"🛍️ <b>{escape(product['name'])}</b>\n"
            f"🔢 Quantity: <code>{new_qty}</code>\n"
            f"💵 Total: <b>{total_str}</b>\n\n"
            "Neeche buttons se aur change karein ya Confirm dabayein:",
            reply_markup=quantity_bottom_keyboard(product_id, new_qty),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


@dp.message(F.text.startswith("📦 Qty: "))
async def show_current_qty_info(message: Message):
    await message.answer("Yeh aapki current quantity hai. ➖ ya ➕ dabakar badlein.")


@dp.message(F.text.startswith("✅ Confirm #"))
async def confirm_checkout_bottom(message: Message):
    try:
        raw = message.text.replace("✅ Confirm #", "")
        product_id_str, qty_str = raw.split("_")
        product_id = int(product_id_str)
        quantity = int(qty_str)

        product = db.get_product(product_id)
        if not product or product["stock"] < quantity:
            await message.answer("Stock kam ho chuka hai, catalog se dobara try karein.", reply_markup=main_bottom_keyboard())
            return

        curr = db.get_user_currency(message.from_user.id)
        unit_price = product["price_inr"] if curr == "INR" else product["price_usdt"]
        total_cost = round(unit_price * quantity, 2)
        total_str = f"₹{total_cost}" if curr == "INR" else f"{total_cost} USDT"

        text = (
            f"📦 <b>Order Summary:</b>\n\n"
            f"Product: <b>{escape(product['name'])}</b>\n"
            f"Total Quantity: <code>{quantity}</code>\n"
            f"Payable Amount: <b>{total_str}</b>\n\n"
            "👇 <i>Neeche diye gaye buttons se payment method select karein:</i>"
        )
        await message.answer(
            text,
            reply_markup=payment_method_bottom_keyboard(product_id, quantity),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")


# ------------------------------------------------------------------
# Payment Handlers (UPI & Binance)
# ------------------------------------------------------------------
@dp.message(F.text.startswith("💳 Pay UPI #"))
async def pay_upi_handler(message: Message):
    try:
        raw = message.text.replace("💳 Pay UPI #", "")
        product_id_str, qty_str = raw.split("x")
        product_id = int(product_id_str.strip())
        quantity = int(qty_str.strip())

        product = db.get_product(product_id)
        if not product or product["stock"] < quantity:
            await message.answer("Stock khatam ho chuka hai.", reply_markup=main_bottom_keyboard())
            return

        total_inr = round(product["price_inr"] * quantity, 2)
        order_id = db.create_order(
            user_id=message.from_user.id,
            username=message.from_user.username,
            product_id=product_id,
            quantity=quantity,
            amount=total_inr,
            currency="INR",
            payment_method="upi",
        )

        link = razorpay_upi.create_upi_payment_link(
            order_db_id=order_id,
            amount_inr=total_inr,
            description=f"{product['name']} x{quantity}",
            customer_name=message.from_user.full_name,
            callback_url=f"{config.PUBLIC_BASE_URL}/webhook/razorpay",
        )
        db.set_gateway_order_id(order_id, link["id"])

        text = (
            f"💳 <b>UPI Payment Link</b>\n\n"
            f"Product: {escape(product['name'])}\n"
            f"Quantity: {quantity}\n"
            f"Total Amount: ₹{total_inr}\n\n"
            f"Neeche diye link par pay karein (GPay/PhonePe/Paytm):\n{link['short_url']}\n\n"
            f"Payment ke baad status check karein, accounts yahin milenge."
        )
        await message.answer(
            text,
            reply_markup=check_payment_keyboard(order_id),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except Exception as e:
        logger.exception("UPI Error")
        await message.answer(f"❌ Payment Error: {escape(str(e))}")


@dp.message(F.text.startswith("🪙 Pay Binance #"))
async def pay_binance_handler(message: Message):
    try:
        raw = message.text.replace("🪙 Pay Binance #", "")
        product_id_str, qty_str = raw.split("x")
        product_id = int(product_id_str.strip())
        quantity = int(qty_str.strip())

        product = db.get_product(product_id)
        if not product or product["stock"] < quantity:
            await message.answer("Stock khatam ho chuka hai.", reply_markup=main_bottom_keyboard())
            return

        total_usdt = round(product["price_usdt"] * quantity, 2)
        order_id = db.create_order(
            user_id=message.from_user.id,
            username=message.from_user.username,
            product_id=product_id,
            quantity=quantity,
            amount=total_usdt,
            currency="USDT",
            payment_method="binance",
        )

        result = binance_pay.create_order(
            order_db_id=order_id,
            amount_usdt=total_usdt,
            description=f"{product['name']} x{quantity}",
            goods_name=f"{product['name']} x{quantity}",
        )
        if result.get("status") != "SUCCESS":
            raise Exception(result.get("errorMessage", "Binance error"))

        data = result["data"]
        db.set_gateway_order_id(order_id, data["prepayId"])

        text = (
            f"🪙 <b>Binance Pay Payment</b>\n\n"
            f"Product: {escape(product['name'])}\n"
            f"Quantity: {quantity}\n"
            f"Total: {total_usdt} USDT\n\n"
            f"Neeche link se payment complete karein:\n{data['checkoutUrl']}"
        )
        await message.answer(
            text,
            reply_markup=check_payment_keyboard(order_id),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except Exception as e:
        logger.exception("Binance Error")
        await message.answer(f"❌ Payment Error: {escape(str(e))}")


# ------------------------------------------------------------------
# Auto Delivery & Webhook Notification
# ------------------------------------------------------------------
@dp.callback_query(F.data.startswith("check_"))
async def check_status(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Order nahi mila.", show_alert=True)
        return

    if order["status"] == "paid":
        await callback.message.edit_text("✅ Payment confirmed! Accounts deliver kar diye gaye hain.")
    else:
        await callback.answer("⏳ Payment abhi pending hai.", show_alert=True)


async def notify_payment_success(order: dict):
    product = db.get_product(order["product_id"])
    pname = escape(product["name"]) if product else "Item"
    quantity = order.get("quantity", 1)

    delivered_accounts = db.deliver_accounts_for_order(order["product_id"], order["id"], quantity)

    if delivered_accounts:
        acc_list = "\n\n".join([f"<code>{escape(acc)}</code>" for acc in delivered_accounts])
        delivery_msg = (
            f"🎁 <b>Aapke Accounts Deliver Ho Gaye ({len(delivered_accounts)}):</b>\n\n"
            f"{acc_list}\n\n"
            f"⚠️ <i>Kripya details check aur save kar lein.</i>"
        )
    else:
        delivery_msg = "⚠️ Payment received ho gayi hai, par instant stock out hai. Admin manually deliver karenge."

    try:
        await bot.send_message(
            order["user_id"],
            f"✅ <b>Payment Received!</b>\n\n"
            f"Order #{order['id']} — <b>{pname}</b> x{quantity}\n"
            f"Amount: {order['amount']} {order['currency']}\n\n"
            f"{delivery_msg}",
            parse_mode=ParseMode.HTML
        )
    except Exception:
        logger.exception("Failed to notify user %s", order.get("user_id"))
