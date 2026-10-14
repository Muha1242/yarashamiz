"""Vercel serverless webhook — aiogram botini Vercel'da ishga tushuradi.

Vercel'da fon jarayoni yo'q, shuning uchun bot long polling o'rniga
**webhook** rejimida ishlaydi. Har bir Telegram xabari shu funksiyani
chaqiradi va quyidagilar bajariladi:

    1. Redis'dan  bot.db  ->  /tmp/bot.db   (pull)
    2. update aiogram Dispatcher orqali qayta ishlanadi
    3. /tmp/bot.db  ->  Redis                (push)

Webhook manzili:  https://<loyiha>.vercel.app/api/tg
"""
import asyncio
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

# bot.py repo ildizida — uni import qilish uchun yo'lni qo'shamiz
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# bot.py import paytida shu yo'lni o'qiydi (Vercel'da faqat /tmp yoziladi)
os.environ.setdefault("DB_PATH", "/tmp/bot.db")

import vstore  # noqa: E402

SECRET = os.environ.get("WEBHOOK_SECRET", "")


def _process(body: bytes) -> None:
    """Bitta Telegram update'ini qayta ishlaydi."""
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.types import Update
    import bot as B

    # --- 1. Bazani yangilash ---
    B.db.reopen()
    if vstore.pull(B.db.path):
        B.db.reopen()
        B.init_db(B.db.conn)

    # --- 2. Update'ni qayta ishlash ---
    update = Update.model_validate_json(body, context={"bot": B.bot})
    B.bot.session = AiohttpSession()          # har chaqiruvda toza sessiya

    async def run():
        try:
            await B.dp.feed_update(B.bot, update)
        finally:
            await B.bot.session.close()

    asyncio.run(run())

    # --- 3. Bazani saqlash ---
    B.db.commit()
    vstore.push(B.db.path)


class handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, text: str = "ok") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode())

    def do_POST(self) -> None:
        if SECRET and self.headers.get("x-telegram-bot-api-secret-token") != SECRET:
            return self._reply(401, "unauthorized")
        try:
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            _process(body)
        except Exception:
            # Telegram qayta-qayta yubormasligi uchun baribir 200 qaytaramiz
            traceback.print_exc()
        self._reply(200, "ok")

    def do_GET(self) -> None:
        self._reply(200, "Yarashamiz webhook ishlayapti")
