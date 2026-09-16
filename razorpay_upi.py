"""
Razorpay ke through UPI payment.
Razorpay 'Payment Links' API use kar rahe hain - isse ek link/QR ban jata hai
jo user UPI apps (GPay, PhonePe, Paytm) se pay kar sakta hai.

Docs: https://razorpay.com/docs/api/payments/payment-links/
"""
import razorpay
import hmac
import hashlib
from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_upi_payment_link(order_db_id: int, amount_inr: float, description: str,
                             customer_name: str, callback_url: str):
    """
    Razorpay Payment Link banata hai. Amount paise mein bhejna padta hai (INR * 100).
    reference_id mein apna internal order id daal rahe hain taaki webhook mein match kar sakein.
    """
    payload = {
        "amount": int(round(amount_inr * 100)),
        "currency": "INR",
        "description": description,
        "reference_id": f"order_{order_db_id}",
        "customer": {
            "name": customer_name or "Telegram User",
        },
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "callback_url": callback_url,
        "callback_method": "get",
    }
    link = client.payment_link.create(payload)
    # link['id'] -> plink_xxxx  (ye hum gateway_order_id ke roop mein store karenge)
    # link['short_url'] -> user ko bhejne wala payment link/QR page
    return link


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Razorpay webhook signature verify karta hai (security ke liye zaroori,
    warna koi bhi fake 'payment success' bhej sakta hai).
    """
    if not RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
