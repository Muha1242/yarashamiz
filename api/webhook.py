"""Vercel serverless: Telegram webhook qabul qiluvchi.

Webhook manzili:  https://<loyiha>.vercel.app/api/webhook
(uni /api/setup?s=SETUP_KEY orqali ro'yxatdan o'tkazasiz)
"""
import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SECRET = os.environ.get("WEBHOOK_SECRET", "")


def _process(body: bytes) -> None:
    from aiogram.types import Update
    import bot as core

    update = Update.model_validate_json(body, context={"bot": core.bot})

    async def run():
        try:
            await core.dp.feed_update(core.bot, update)
        finally:
            # serverless: har chaqiruvdan keyin sessiyani yopamiz
            try:
                await core.bot.session.close()
            except Exception:
                pass

    asyncio.run(run())


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if SECRET and self.headers.get("x-telegram-bot-api-secret-token") != SECRET:
            self.send_response(401)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            _process(body)
        except Exception:  # noqa: BLE001
            # Telegram qayta-qayta yubormasligi uchun baribir 200 qaytaramiz
            traceback.print_exc()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Yarashamiz webhook ishlayapti".encode())

    def log_message(self, *args) -> None:
        pass
