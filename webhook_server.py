"""
Yeh server Razorpay aur Binance dono se payment confirmation webhooks receive karta hai.
Jab payment successful hoti hai, DB mein order 'paid' mark hota hai aur bot user ko
Telegram par message bhejta hai.

IMPORTANT: Is server ko public HTTPS URL par host karna hoga (VPS + domain + SSL,
ya ngrok jaise tool se testing ke liye) taaki Razorpay/Binance webhook bhej sakein.
"""
import json
import logging
from fastapi import FastAPI, Request, Header, HTTPException

import database as db
from payments import razorpay_upi, binance_pay
import bot as bot_module   # bot instance + notify_payment_success yahan se aata hai

logger = logging.getLogger(__name__)
app = FastAPI()


# ------------------------------------------------------------------
# Razorpay webhook
# Dashboard mein webhook URL set karo: https://yourdomain.com/webhook/razorpay
# Event subscribe karo: payment_link.paid
# ------------------------------------------------------------------
@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    raw_body = await request.body()

    if not razorpay_upi.verify_webhook_signature(raw_body, x_razorpay_signature or ""):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(raw_body)
    event = payload.get("event")

    if event == "payment_link.paid":
        plink_id = payload["payload"]["payment_link"]["entity"]["id"]
        order = db.mark_order_paid(plink_id)
        if order:
            await bot_module.notify_payment_success(order)
            logger.info(f"Order {order['id']} marked paid via Razorpay")

    return {"status": "ok"}


# Razorpay callback_url (browser redirect after payment) - optional UX nicety
@app.get("/razorpay/callback")
async def razorpay_callback():
    return {"message": "Payment processed. Aap Telegram par wapas ja sakte hain."}


# ------------------------------------------------------------------
# Binance Pay webhook
# Merchant dashboard mein webhook URL set karo: https://yourdomain.com/webhook/binance
# ------------------------------------------------------------------
@app.post("/webhook/binance")
async def binance_webhook(request: Request):
    raw_body = await request.body()
    headers = dict(request.headers)

    if not binance_pay.verify_webhook(headers, raw_body):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(raw_body)
    biz_type = payload.get("bizType")
    biz_status = payload.get("bizStatus")

    if biz_type == "PAY" and biz_status == "PAY_SUCCESS":
        data = json.loads(payload["data"])
        prepay_id = data.get("prepayId")
        order = db.mark_order_paid(prepay_id)
        if order:
            await bot_module.notify_payment_success(order)
            logger.info(f"Order {order['id']} marked paid via Binance Pay")

    # Binance expects this exact response format
    return {"returnCode": "SUCCESS", "returnMessage": None}


@app.get("/health")
async def health():
    return {"status": "ok"}
