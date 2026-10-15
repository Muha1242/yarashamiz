"""Vercel serverless: webhookni ro'yxatdan o'tkazish.

Deploy'dan keyin brauzerda bir marta oching:
    https://SIZNING-DOMEN.vercel.app/api/setup?s=SETUP_KEY
SETUP_KEY muhit o'zgaruvchisiga o'zingiz xohlagan maxfiy so'z qo'ying.
"""
import asyncio
import os
from http.server import BaseHTTPRequestHandler

import bot as core  # noqa: E402


async def _set():
    # Har chaqiruvda toza sessiya - aks holda ikkinchi chaqiruvda
    # "Timeout context manager should be used inside a task" xatosi chiqadi
    from aiogram.client.session.aiohttp import AiohttpSession
    core.bot.session = AiohttpSession()

    a = (os.environ.get("WEBAPP_URL") or "").strip().rstrip("/")
    if not a:
        base = (os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
                or os.environ.get("APP_URL")
                or os.environ.get("VERCEL_URL") or "").strip().rstrip("/")
        if base and not base.lower().startswith("http"):
            base = "https://" + base
        a = base
    url = a + "/api/webhook"
    await core.bot.set_webhook(url, drop_pending_updates=True)
    try:
        await core.bot.session.close()
    except Exception:
        pass
    return url


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        key = ""
        if "?s=" in self.path:
            key = self.path.split("?s=", 1)[1].split("&")[0]
        if key != os.environ.get("SETUP_KEY", ""):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"forbidden")
            return
        try:
            url = asyncio.run(_set())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"webhook set: {url}".encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, *args):
        pass
