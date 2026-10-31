"""Vercel serverless: webhookni ro'yxatdan o'tkazish.

Deploy'dan keyin brauzerda bir marta oching:
    https://SIZNING-DOMEN.vercel.app/api/setup?s=SETUP_KEY
SETUP_KEY muhit o'zgaruvchisiga o'zingiz xohlagan maxfiy so'z qo'ying.
"""
import asyncio
import hmac
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bot as core  # noqa: E402


async def _set():
    # Har chaqiruvda toza sessiya - aks holda ikkinchi chaqiruvda
    # "Timeout context manager should be used inside a task" xatosi chiqadi
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
    core.bot.session = AiohttpSession()

    a = (os.environ.get("WEBAPP_URL") or "").strip().rstrip("/")
    if a:
        if not a.lower().startswith("http"):
            a = "https://" + a
        sp = urllib.parse.urlsplit(a)
        root = f"{sp.scheme}://{sp.netloc}" if sp.netloc else a
    else:
        base = (os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
                or os.environ.get("APP_URL")
                or os.environ.get("VERCEL_URL") or "").strip().rstrip("/")
        if base and not base.lower().startswith("http"):
            base = "https://" + base
        root = base
    if not root:
        raise RuntimeError("WEBAPP_URL (yoki VERCEL_PROJECT_PRODUCTION_URL) "
                           "aniqlanmadi — webhook manzilini bilmayapman")
    url = root.rstrip("/") + "/api/webhook"
    await core.bot.set_webhook(url, drop_pending_updates=True)
    # menyu va tavsif - bot ommaga chiroyli ko'rinadi
    try:
        await core.bot.set_my_commands([
            BotCommand(command="start", description="Boshlash / Ilovani ochish"),
            BotCommand(command="menu", description="Asosiy menyu"),
            BotCommand(command="invite", description="Do'stlarni taklif qilish 🎁"),
            BotCommand(command="reminders", description="Eslatmalar yoqish/o'chirish"),
            BotCommand(command="voice", description="🎤 Ovozli xat (premium)"),
            BotCommand(command="maslahat", description="💞 AI maslahat (premium)"),
            BotCommand(command="promo", description="🎟 Promo-kodni faollashtirish"),
            BotCommand(command="app", description="Ilovani ochish"),
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
    # menyu tugmasi ham Mini App bo'lishi shart (aks holda initData bo'lmaydi)
    try:
        await core.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="💌 Ilova", web_app=WebAppInfo(url=f"{a}/")))
    except Exception:  # noqa: BLE001
        pass
    try:
        await core.bot.session.close()
    except Exception:
        pass
    # username ni keshga yozamiz — Mini App tarmoqqa chiqmasin
    try:
        me = await core.bot.get_me()
        if me and me.username:
            core.st.r.set("ybot:username", me.username)
    except Exception:  # noqa: BLE001
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
