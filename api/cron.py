"""Vercel Cron — kunlik eslatmalar (missiya / seriya).

`vercel.json` dagi `crons` bo'limi bu manzilni kuniga bir marta chaqiradi
(masalan 15:00 UTC = 20:00 O'zbekiston vaqtida).

Qo'lda sinash:  https://<loyiha>.vercel.app/api/cron
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

os.environ.setdefault("DB_PATH", "/tmp/bot.db")

import vstore  # noqa: E402

CRON_SECRET = os.environ.get("CRON_SECRET", "")


def _run() -> None:
    from aiogram.client.session.aiohttp import AiohttpSession
    import bot as B

    # 1. Bazani yangilash
    B.db.reopen()
    if vstore.pull(B.db.path):
        B.db.reopen()
        B.init_db(B.db.conn)

    # 2. Eslatmalarni yuborish (bir marta)
    B.bot.session = AiohttpSession()

    async def go():
        try:
            await B.reminders_once()
        finally:
            await B.bot.session.close()

    asyncio.run(go())

    # 3. Bazani saqlash
    B.db.commit()
    vstore.push(B.db.path)


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self) -> None:
        if CRON_SECRET and self.headers.get("authorization") != "Bearer " + CRON_SECRET:
            return self._json(401, {"err": "unauthorized"})
        try:
            _run()
            self._json(200, {"ok": True, "job": "reminders"})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._json(200, {"ok": False, "error": repr(e)})

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()
