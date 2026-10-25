"""Vercel Cron — kunlik eslatmalar (missiya / kunlik savol / seriya).

`vercel.json` dagi crons bo'limi bu manzilni kuniga bir marta chaqiradi
(15:00 UTC = 20:00 O'zbekiston).

Qo'lda sinash:  https://<loyiha>.vercel.app/api/cron
"""
import asyncio
import hmac
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CRON_SECRET = os.environ.get("CRON_SECRET", "")


def _run() -> dict:
    """Eslatmalarni yig'ib, foydalanuvchilarga yuboradi."""
    import bot as core
    import store as st

    # Bir vaqtda ikki cron (yoki spam) ishlamasin; 10 daqiqadan keyin retry mumkin
    with st.lock(f"cron:rem:{st.today()}", ttl=600) as ok:
        if not ok:
            return {"ok": True, "job": "reminders", "skipped": "already_running"}

        async def go():
            sent, failed = 0, 0
            try:
                jobs = await core.run_reminders()
                for u, msg, kind in jobs:
                    try:
                        await core.bot.send_message(u, msg)
                        # faqat muvaffaqiyatli yuborilgandan keyin belgilaymiz
                        st.mark(u, kind)
                        sent += 1
                    except Exception:  # noqa: BLE001
                        failed += 1
            finally:
                try:
                    await core.bot.session.close()
                except Exception:
                    pass
            return sent, failed

        sent, failed = asyncio.run(go())
        return {"ok": True, "job": "reminders", "sent": sent, "failed": failed}


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self) -> None:
        if not CRON_SECRET:
            # Fail closed: CRON_SECRET o'rnatilmasa endpoint ochiq qolmasin
            return self._json(503, {"err": "CRON_SECRET o'rnatilmagan"})
        got = self.headers.get("authorization") or ""
        try:
            ok = hmac.compare_digest(got, "Bearer " + CRON_SECRET)
        except TypeError:
            ok = False
        if not ok:
            return self._json(401, {"err": "unauthorized"})
        try:
            self._json(200, _run())
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._json(200, {"ok": False, "error": repr(e)})

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def log_message(self, *args) -> None:
        pass
