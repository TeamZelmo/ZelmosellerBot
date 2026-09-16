"""
Entry point jo dono ko sath me run karta hai:
1. Telegram Bot (Polling mode)
2. FastAPI Webhook Server (Razorpay aur Binance confirmations ke liye)

Run: python main.py
"""
import asyncio
import logging
import uvicorn

import config
import database as db
import bot as bot_module
from webhook_server import app as webhook_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_bot():
    await bot_module.dp.start_polling(bot_module.bot)


async def run_webhook_server():
    server_config = uvicorn.Config(
        webhook_app,
        host="0.0.0.0",
        port=config.WEBHOOK_SERVER_PORT,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main():
    db.init_db()
    logger.info("Starting bot + webhook server together...")
    await asyncio.gather(
        run_bot(),
        run_webhook_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
