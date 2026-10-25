"""Vercel serverless: Telegram webhook qabul qiluvchi.

Webhook manzili:  https://<loyiha>.vercel.app/api/webhook
(uni /api/setup?s=SETUP_KEY orqali ro'yxatdan o'tkazasiz)
"""
import asyncio
import hmac
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MAX_BODY = 1024 * 1024       # Telegram update 1 MB dan katta bo'lmaydi


def _secret():
    """Webhook tokeni: env yoki /api/setup saqlagan Redis kaliti.

    Token topilmasa webhook yopiq (fail closed) — aks holda istalgan odam
    soxta Update yuborib, istalgan foydalanuvchi bo'lib ko'rinishi mumkin.
    Har chaqiruvda o'qiymiz: setup tokenni almashtirsa, issiq lambda ham
    darhol yangi tokenni ko'radi.
    """
    s = (os.environ.get("WEBHOOK_SECRET") or "").strip()
    if not s:
        try:
            import store as st
            s = st.r.get("ybot:webhook_secret") or ""
        except Exception:  # noqa: BLE001
            s = ""
    return s


def _process(body: bytes) -> None:
    from aiogram.types import Update
    import bot as core

    # Har chaqiruv yangi event loop -> FSM Redis klientini yangilaymiz
    core.reset_storage()

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
        secret = _secret()
        got = self.headers.get("x-telegram-bot-api-secret-token") or ""
        try:
            ok = bool(secret) and hmac.compare_digest(got, secret)
        except TypeError:      # non-ASCII header
            ok = False
        if not ok:
            self.send_response(401)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > MAX_BODY:
                self.send_response(413)
                self.end_headers()
                return
            body = self.rfile.read(length) if length else b"{}"
            _process(body)
        except Exception:  # noqa: BLE001
            # Xatoni Redis'ga yozamiz - /api/check?err=1 orqali ko'rish mumkin
            tb = traceback.format_exc()
            traceback.print_exc()
            try:
                import redis as _r
                rc = _r.from_url(os.environ.get("REDIS_URL") or "",
                                 socket_timeout=5, decode_responses=True)
                rc.set("ybot:lasterror", tb[-1200:])
                rc.set("ybot:lastupdate", body[:400])
            except Exception:
                pass
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Yarashamiz webhook ishlayapti".encode())

    def log_message(self, *args) -> None:
        pass
