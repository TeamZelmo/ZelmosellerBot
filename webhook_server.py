import json
import logging
import razorpay_upi
import binance_pay
from fastapi import FastAPI, Request, Response, status

import database as db
import bot as bot_module


logger = logging.getLogger(__name__)

app = FastAPI(title="Payment Webhook Receiver")


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Webhook server running"}


# ------------------------------------------------------------------
# Razorpay UPI Webhook Endpoint
# URL: https://yourdomain.com/webhook/razorpay
# ------------------------------------------------------------------
@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # 1. Signature Verify karna
    if not razorpay_upi.verify_webhook_signature(raw_body, signature):
        logger.warning("Invalid Razorpay webhook signature")
        return Response(content="Invalid signature", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        data = json.loads(raw_body.decode())
        event = data.get("event")

        # Payment link successful hone par
        if event == "payment_link.paid":
            payment_link_entity = data.get("payload", {}).get("payment_link", {}).get("entity", {})
            gateway_order_id = payment_link_entity.get("id")  # plink_xxxx

            if gateway_order_id:
                # Order DB me paid mark karein
                order = db.mark_order_paid(gateway_order_id)
                if order:
                    logger.info(f"Razorpay payment confirmed for order ID: {order['id']}")
                    # Bot se customer ko proactive message bhejna
                    await bot_module.notify_payment_success(order)

        return {"status": "ok"}
    except Exception as e:
        logger.exception("Error processing Razorpay webhook")
        return Response(content=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------------------------------------------------
# Binance Pay Webhook Endpoint
# URL: https://yourdomain.com/webhook/binance
# ------------------------------------------------------------------
@app.post("/webhook/binance")
async def binance_webhook(request: Request):
    raw_body = await request.body()
    headers = dict(request.headers)

    # 1. Binance Signature Verify karna
    if not binance_pay.verify_webhook_signature(headers, raw_body):
        logger.warning("Invalid Binance Pay webhook signature")
        return Response(content="Invalid signature", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        data = json.loads(raw_body.decode())
        biz_status = data.get("bizStatus")

        # Payment complete hone par
        if biz_status == "PAY_SUCCESS":
            data_dict = json.loads(data.get("data", "{}")) if isinstance(data.get("data"), str) else data.get("data", {})
            prepay_id = data_dict.get("prepayId")

            if prepay_id:
                # Order DB me paid mark karein
                order = db.mark_order_paid(prepay_id)
                if order:
                    logger.info(f"Binance Pay payment confirmed for order ID: {order['id']}")
                    # Bot se customer ko notification bhejna
                    await bot_module.notify_payment_success(order)

        # Binance ko confirm return status dena zaroori hai
        return {"returnCode": "SUCCESS", "returnMessage": None}
    except Exception as e:
        logger.exception("Error processing Binance webhook")
        return Response(content=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
