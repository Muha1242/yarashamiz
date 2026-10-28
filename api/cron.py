"""Vercel Cron — kunlik eslatmalar (missiya / kunlik savol / seriya).

`vercel.json` dagi crons bo'limi bu manzilni kuniga bir marta chaqiradi
(15:00 UTC = 20:00 O'zbekiston).

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

CRON_SECRET = os.environ.get("CRON_SECRET", "")
MAX_MSGS = int(os.environ.get("CRON_MAX_MSGS", "600"))
CONCURRENCY = int(os.environ.get("CRON_CONCURRENCY", "12"))
RATE = float(os.environ.get("CRON_RATE", "28"))      # xabar/soni (Telegram ~30/s)


class _Rate:
    """Global token-bucket: barcha parallel yuborishlar jami RATE/s dan oshmaydi."""

    def __init__(self, rate: float):
        self.rate = max(1.0, rate)
        self.next_at = 0.0
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            if now < self.next_at:
                await asyncio.sleep(self.next_at - now)
                now = self.next_at
            self.next_at = now + 1.0 / self.rate


def _run() -> dict:
    """Eslatmalarni yig'ib, rate-limit bilan parallel yuboradi."""
    import bot as core
    from aiogram.exceptions import TelegramRetryAfter

    async def go():
        pairs = await core.run_reminders(limit=MAX_MSGS)
        capped = len(pairs) >= MAX_MSGS
        sem = asyncio.Semaphore(CONCURRENCY)
        rate = _Rate(RATE)
        sent, failed = 0, 0

        async def one(u, text, kind):
            nonlocal sent, failed
            async with sem:
                await rate.wait()
                try:
                    for attempt in (1, 2):
                        try:
                            await core.bot.send_message(u, text)
                            break
                        except TelegramRetryAfter as e:
                            if attempt == 2:
                                raise
                            await asyncio.sleep(min(int(e.retry_after or 1), 30))
                except Exception:  # noqa: BLE001
                    failed += 1
                    return
                sent += 1
                try:
                    if kind.startswith("cap:"):
                        core.st.capsule_notified(int(kind[4:]), u)
                    elif kind:
                        core.st.mark(u, kind)        # faqat muvaffaqiyatdan keyin
                except Exception:  # noqa: BLE001
                    pass

        try:
            await asyncio.gather(*[one(*p) for p in pairs])
        finally:
            try:
                await core.bot.session.close()
            except Exception:
                pass
        return sent, failed, len(pairs), capped

    sent, failed, total, capped = asyncio.run(go())
    return {"ok": True, "job": "reminders", "sent": sent, "failed": failed,
            "total": total, "capped": capped}


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
        # dublikat xabar bo'lmasligi uchun har doim 5 daqiqalik qulf
        try:
            import redis as _r
            rc = _r.from_url(os.environ.get("REDIS_URL") or "",
                             socket_timeout=3, decode_responses=True)
            if not rc.set("cron:lock", 1, nx=True, ex=300):
                return self._json(429, {"ok": False, "err": "too_often",
                                        "hint": "5 daqiqadan keyin qayta urinib ko'ring"})
        except Exception:  # noqa: BLE001
            pass
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
