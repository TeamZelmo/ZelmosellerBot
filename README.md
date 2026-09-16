# Telegram Product-Selling Bot (UPI + Binance Pay)

Ek Telegram bot jisse log products browse kar sakein aur **UPI** (Razorpay ke through)
ya **Binance Pay** (crypto/USDT) se payment kar sakein.

## Features
- Product catalog (inline buttons)
- UPI payment via Razorpay Payment Links (GPay/PhonePe/Paytm sab chalega)
- Crypto payment via Binance Pay (USDT)
- Automatic payment confirmation via webhooks — jaise hi payment hoti hai, bot user ko
  Telegram par message bhejta hai aur stock update karta hai
- Simple admin command se product add karna
- `/orders` command se apne orders check karna

## Project Structure
```
telegram_shop_bot/
├── main.py               # Entry point - bot + webhook server dono chalata hai
├── bot.py                 # Bot handlers (catalog, checkout, etc.)
├── webhook_server.py      # FastAPI server - payment confirmations receive karta hai
├── database.py            # SQLite database functions
├── keyboards.py           # Telegram inline keyboards
├── config.py               # Environment variables load karta hai
├── payments/
│   ├── razorpay_upi.py    # Razorpay UPI integration
│   └── binance_pay.py     # Binance Pay integration
├── requirements.txt
└── .env.example
```

## Setup Steps

### 1. Bot Token Lena
- Telegram par [@BotFather](https://t.me/BotFather) ko message karo
- `/newbot` command se naya bot banao, token copy karo

### 2. Razorpay Account (UPI ke liye)
- [razorpay.com](https://razorpay.com) par sign up karo, KYC/business verification complete karo
- Dashboard → Settings → API Keys se `Key ID` aur `Key Secret` lo
- Dashboard → Account & Settings → Webhooks mein ek webhook add karo:
  - URL: `https://yourdomain.com/webhook/razorpay`
  - Event: `payment_link.paid`
  - Yahan jo "secret" set karoge, wahi `RAZORPAY_WEBHOOK_SECRET` mein daalna

### 3. Binance Pay Merchant Account
- [merchant.binance.com](https://merchant.binance.com) par apply karo (business verification lagta hai)
- API Management se `API Key` aur `Secret Key` generate karo
- Webhook URL set karo: `https://yourdomain.com/webhook/binance`

### 4. Environment Setup
```bash
cd telegram_shop_bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Ab .env file kholo aur apni actual keys daalo
```

### 5. Products Add Karna
Bot start karne ke baad, apne Telegram user ID (jo `.env` mein `ADMIN_IDS` mein daali hai)
se bot ko yeh command bhejo:

```
/addproduct T-Shirt | Cotton black t-shirt, size M | 499 | 6 | 50
```

Format: `Name | Description | price_inr | price_usdt | stock`

### 6. Bot Run Karna
```bash
python main.py
```

Isse bot polling shuru ho jayega **aur** webhook server bhi port 8000 par chalega, dono ek saath.

### 7. Webhooks Public Karna (Important!)
Razorpay/Binance ko webhook bhejne ke liye tumhara server **public HTTPS URL** par hona
chahiye. Do options:

**Local testing ke liye (ngrok):**
```bash
ngrok http 8000
```
Jo HTTPS URL milega (e.g. `https://abcd1234.ngrok-free.app`), use `.env` mein
`PUBLIC_BASE_URL` mein daalo aur Razorpay/Binance dashboard ke webhook URLs mein bhi
wahi domain use karo.

**Production ke liye:** VPS (DigitalOcean, AWS, Hetzner) par deploy karo, Nginx + SSL
(Let's Encrypt / Certbot) laga ke apna domain point karo.

## Important Notes
- `RAZORPAY_KEY_ID` shuru mein `rzp_test_` se testing mode mein use karo, phir live keys
  par switch karo jab ready ho
- Webhook signature verification zaroori hai (already implemented) — isse koi fake
  "payment success" nahi bhej sakta
- Binance Pay aur Razorpay dono ko **registered business** chahiye hota hai live payments
  ke liye — individual account se sirf test mode chalega
- Database SQLite hai jo chhoti/medium scale ke liye theek hai; zyada traffic ho to
  PostgreSQL mein migrate karna better hoga

## Admin Commands
| Command | Description |
|---|---|
| `/addproduct Name \| Desc \| price_inr \| price_usdt \| stock` | Naya product add karo |

## User Commands
| Command | Description |
|---|---|
| `/start` | Bot shuru karo, catalog dikhega |
| `/shop` | Products dekho |
| `/orders` | Apne orders dekho |
