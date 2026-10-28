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
MAX_MSGS = int(os.environ.get("CRON_MAX_MSGS", "1200"))
CONCURRENCY = int(os.environ.get("CRON_CONCURRENCY", "12"))


def _run() -> dict:
    """Eslatmalarni yig'ib, parallel (lekin rate-limit bilan) yuboradi."""
    import bot as core

    async def go():
        pairs = await core.run_reminders(limit=MAX_MSGS)
        sem = asyncio.Semaphore(CONCURRENCY)
        sent, failed = 0, 0
        cap_done = set()

        async def one(u, text, kind):
            nonlocal sent, failed
            async with sem:
                try:
                    await core.bot.send_message(u, text)
                except Exception:  # noqa: BLE001
                    failed += 1
                    return
                sent += 1
                try:
                    if kind.startswith("cap:"):
                        cid = int(kind[4:])
                        if cid not in cap_done:      # bir kapsula bir marta
                            cap_done.add(cid)
                            core.st.capsule_notified(cid)
                    elif kind:
                        core.st.mark(u, kind)        # faqat muvaffaqiyatdan keyin
                except Exception:  # noqa: BLE001
                    pass
                await asyncio.sleep(0.03)            # ~30 xabar/s limit

        try:
            await asyncio.gather(*[one(*p) for p in pairs])
        finally:
            try:
                await core.bot.session.close()
            except Exception:
                pass
        return sent, failed, len(pairs)

    sent, failed, total = asyncio.run(go())
    return {"ok": True, "job": "reminders", "sent": sent, "failed": failed,
            "total": total}


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
        if not CRON_SECRET:
            # secret yo'q bo'lsa — spam bo'lmasligi uchun 10 daqiqada bir marta
            try:
                import redis as _r
                rc = _r.from_url(os.environ.get("REDIS_URL") or "",
                                 socket_timeout=3, decode_responses=True)
                if not rc.set("cron:lock", 1, nx=True, ex=600):
                    return self._json(429, {"ok": False, "err": "too_often"})
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
