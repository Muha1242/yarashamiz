"""Vercel serverless webhook - aiogram botini Vercel'da ishga tushuradi.

Vercel'da fon jarayoni yo'q, shuning uchun bot long polling o'rniga
**webhook** rejimida ishlaydi. Har bir Telegram xabari shu funksiyani
chaqiradi va quyidagilar bajariladi:

    1. Redis'dan  bot.db  ->  /tmp/bot.db   (pull)
    2. update aiogram Dispatcher orqali qayta ishlanadi
    3. /tmp/bot.db  ->  Redis                (push)

Xatolar Redis'ga yoziladi - ularni GET so'rov bilan ko'rish mumkin:
    https://<loyiha>.vercel.app/api/tg
"""
import asyncio
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler

# bot.py repo ildizida - uni import qilish uchun yo'lni qo'shamiz
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# bot.py import paytida shu yo'lni o'qiydi (Vercel'da faqat /tmp yoziladi)
os.environ.setdefault("DB_PATH", "/tmp/bot.db")

import vstore  # noqa: E402

SECRET = os.environ.get("WEBHOOK_SECRET", "")

# Vercel bir vaqtda bir nechta so'rovni bir xil instance'da bajarishi mumkin.
# SQLite ulanishi va /tmp/bot.db fayli umumiy bo'lgani uchun ularni ketma-ket
# bajarish shart - aks holda "SQLite objects created in a thread..." xatosi.
DB_LOCK = threading.RLock()
K_ERR = "yarashamiz:lasterror"
K_OK = "yarashamiz:lastok"
K_CNT = "yarashamiz:okcount"
K_ECNT = "yarashamiz:errcount"


def _incr(key: str) -> None:
    try:
        cur = vstore.get_raw(key)
        vstore.set_raw(key, str(int(cur or 0) + 1))
    except Exception:
        pass


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

    # --- 3. Bazani saqlash ---
    # Xato bo'lsa ham saqlaymiz: aks holda bajarilgan o'zgarishlar yo'qoladi
    # (masalan touch() yozgan seriya, xabar yuborishda xato bo'lsa).
    try:
        asyncio.run(run())
    finally:
        B.db.commit()
        vstore.push(B.db.path)


def _diag() -> dict:
    """Diagnostika: oxirgi xato, hisoblagichlar, baza statistikasi."""
    with DB_LOCK:
        return _diag_locked()


def _diag_locked() -> dict:
    info = {
        "service": "yarashamiz webhook",
        "redis": vstore.ENABLED,
        "db": os.environ.get("DB_PATH"),
        "webapp": None,
        "ok_count": vstore.get_raw(K_CNT),
        "err_count": vstore.get_raw(K_ECNT),
        "last_ok": vstore.get_raw(K_OK),
        "last_error": vstore.get_raw(K_ERR),
    }
    try:
        import bot as B
        info["webapp"] = B.URL
        info["token_set"] = bool(B.TOKEN)
        B.db.reopen()
        pulled = vstore.pull(B.db.path)
        info["redis_pulled"] = pulled
        if pulled:
            B.db.reopen()
            B.init_db(B.db.conn)
        info["db_size"] = os.path.getsize(B.db.path) if os.path.exists(B.db.path) else 0
        for t in ("streaks", "letters", "pairs", "ans", "premium", "gifts", "sent"):
            try:
                info["db_" + t] = B.db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
            except Exception as e:  # noqa: BLE001
                info["db_" + t] = "xato: " + repr(e)
    except Exception as e:  # noqa: BLE001
        info["db_error"] = traceback.format_exc()[-800:]
    return info


class handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, text: str, ctype: str = "text/plain; charset=utf-8") -> None:
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if SECRET and self.headers.get("x-telegram-bot-api-secret-token") != SECRET:
            return self._reply(401, "unauthorized")
        try:
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            with DB_LOCK:
                _process(body)
            _incr(K_CNT)
            vstore.set_raw(K_OK, time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc()
            traceback.print_exc()
            try:
                _incr(K_ECNT)
                vstore.set_raw(K_ERR, tb[-1200:])
            except Exception:
                pass
        # Telegram qayta-qayta yubormasligi uchun baribir 200 qaytaramiz
        self._reply(200, "ok")

    def do_GET(self) -> None:
        try:
            body = json.dumps(_diag(), ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            body = json.dumps({"service": "yarashamiz webhook", "diag_error": traceback.format_exc()[-600:]})
        self._reply(200, body, "application/json; charset=utf-8")
