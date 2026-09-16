 """
Binance Pay Merchant API integration - crypto (USDT etc.) payments ke liye.
Flow:
1. create_order() call karo -> Binance ek prepayId + checkout QR/deeplink deta hai
2. User Binance app se pay karta hai
3. Binance webhook bhejta hai -> verify_webhook() se signature check karo -> order paid mark karo
"""
import hashlib
import hmac
import json
import time
import uuid
import requests
from config import BINANCE_PAY_API_KEY, BINANCE_PAY_API_SECRET, BINANCE_PAY_BASE_URL


def _generate_signature(timestamp: str, nonce: str, body: str) -> str:
    payload = f"{timestamp}\n{nonce}\n{body}\n"
    signature = hmac.new(
        BINANCE_PAY_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha512
    ).hexdigest().upper()
    return signature


def _headers(body: str):
    timestamp = str(int(time.time() * 1000))
    nonce = uuid.uuid4().hex[:32]
    signature = _generate_signature(timestamp, nonce, body)
    return {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": timestamp,
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": BINANCE_PAY_API_KEY,
        "BinancePay-Signature": signature,
    }, timestamp, nonce


def create_order(order_db_id: int, amount_usdt: float, description: str, goods_name: str):
    """
    Binance Pay order create karta hai. Returns dict with checkoutUrl / prepayId.
    """
    url = f"{BINANCE_PAY_BASE_URL}/binancepay/openapi/v3/order"
    body_dict = {
        "env": {"terminalType": "APP"},
        "merchantTradeNo": f"order{order_db_id}_{int(time.time())}",
        "orderAmount": round(amount_usdt, 2),
        "currency": "USDT",
        "goods": {
            "goodsType": "02",              # Virtual goods
            "goodsCategory": "Z000",        # Others
            "referenceGoodsId": str(order_db_id),
            "goodsName": goods_name,
            "goodsDetail": description,
        },
    }
    body = json.dumps(body_dict)
    headers, _, _ = _headers(body)
    resp = requests.post(url, headers=headers, data=body, timeout=15)
    return resp.json()


def verify_webhook_signature(headers: dict, raw_body: bytes) -> bool:
    """
    Binance webhook signature verify karta hai.
    """
    timestamp = headers.get("Binancepay-Timestamp") or headers.get("BinancePay-Timestamp")
    nonce = headers.get("Binancepay-Nonce") or headers.get("BinancePay-Nonce")
    signature = headers.get("Binancepay-Signature") or headers.get("BinancePay-Signature")
    if not (timestamp and nonce and signature):
        return False

    payload = f"{timestamp}\n{nonce}\n{raw_body.decode()}\n"
    expected = hmac.new(
        BINANCE_PAY_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha512
    ).hexdigest().upper()
    return hmac.compare_digest(expected, signature)
