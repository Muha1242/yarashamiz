"""Vercel serverless: Telegram webhook qabul qiluvchi."""
import asyncio
import json
from http.server import BaseHTTPRequestHandler

from aiogram.types import Update

import bot as core  # noqa: E402  (asosiy dispatcher va bot obyekti)


async def _process(update):
    try:
        await core.dp.feed_update(core.bot, update)
    finally:
        # serverless: har chaqiruvdan keyin sessiyani yopamiz (event loop muammosi bo'lmasin)
        try:
            await core.bot.session.close()
        except Exception:
            pass


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            update = Update.model_validate(json.loads(body))
            asyncio.run(_process(update))
            code = 200
        except Exception:
            code = 500
        self.send_response(code)
        self.end_headers()

    def log_message(self, *args):
        pass
