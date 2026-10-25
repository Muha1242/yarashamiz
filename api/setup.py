"""Vercel serverless: webhookni ro'yxatdan o'tkazish.

Deploy'dan keyin brauzerda bir marta oching:
    https://SIZNING-DOMEN.vercel.app/api/setup?s=SETUP_KEY
SETUP_KEY muhit o'zgaruvchisiga o'zingiz xohlagan maxfiy so'z qo'ying.
"""
import asyncio
import hmac
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bot as core  # noqa: E402


async def _set():
    # Har chaqiruvda toza sessiya - aks holda ikkinchi chaqiruvda
    # "Timeout context manager should be used inside a task" xatosi chiqadi
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.types import BotCommand
    core.bot.session = AiohttpSession()

    a = core.base_url()
    if not a:
        raise RuntimeError("WEBAPP_URL (yoki VERCEL_PROJECT_PRODUCTION_URL) "
                           "aniqlanmadi — webhook manzilini bilmayapman")
    url = a + "/api/webhook"
    # Webhook maxfiy tokeni: env bo'lsa o'sha, bo'lmasa avtomatik yaratiladi va
    # Redis'ga saqlanadi. webhook.py shu token bilan Telegram so'rovini tekshiradi
    # (aks holda istalgan odam soxta update yuborib, foydalanuvchi bo'lib ko'rinadi).
    secret = (os.environ.get("WEBHOOK_SECRET") or "").strip()
    if not secret:
        try:
            secret = core.st.r.get("ybot:webhook_secret") or ""
        except Exception:  # noqa: BLE001
            secret = ""
    if not secret:
        secret = secrets.token_urlsafe(32)
    try:
        core.st.r.set("ybot:webhook_secret", secret)
    except Exception:  # noqa: BLE001
        pass
    await core.bot.set_webhook(url, drop_pending_updates=True, secret_token=secret)
    # Bot username'ini keshga yozamiz — ilovadagi taklif havolasi sovuq startda
    # ham darhol ishlashi uchun (tarmoqqa har safar chiqmaymiz).
    try:
        me = await core.bot.get_me()
        if me.username:
            core.st.r.set("ybot:username", me.username)
    except Exception:  # noqa: BLE001
        pass
    # menyu va tavsif - bot ommaga chiroyli ko'rinadi
    try:
        await core.bot.set_my_commands([
            BotCommand(command="start", description="Boshlash / Ilovani ochish"),
            BotCommand(command="menu", description="Asosiy menyu"),
            BotCommand(command="link", description="Oxirgi xat havolasini qayta olish"),
            BotCommand(command="invite", description="Do'stlarni taklif qilish 🎁"),
            BotCommand(command="reminders", description="Eslatmalar yoqish/o'chirish"),
            BotCommand(command="help", description="Yordam"),
            BotCommand(command="privacy", description="Maxfiylik"),
            BotCommand(command="feedback", description="Fikr va taklif"),
            BotCommand(command="cancel", description="Bekor qilish"),
        ])
        await core.bot.set_my_short_description(
            "Arazni chiroyli tugating 💌 — xat yozing, yarashing, birga o'ynang.")
        await core.bot.set_my_description(
            "💌 Yarashamiz — sevishganlarni yarashtirish boti.\n\n"
            "✍️ Uzr yoki sevgi xati yozing va havolani juftingizga yuboring.\n"
            "❤️ U «Yarashamiz» desa — juftlik ochiladi.\n"
            "🎮 Birga o'yin o'ynang, kunlik seriya va ball to'plang.\n"
            "💎 Premium: cheksiz xat, AI yordamchi va maxsus shablonlar.")
    except Exception:  # noqa: BLE001
        pass
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
        expected = os.environ.get("SETUP_KEY", "")
        if not expected:
            # SETUP_KEY o'rnatilmagan bo'lsa — webhookni istalgan odam
            # o'zgartirib yubormasligi uchun yopiq qoldiramiz
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"SETUP_KEY env o'zgaruvchisini o'rnating")
            return
        if not hmac.compare_digest(key, expected):
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
