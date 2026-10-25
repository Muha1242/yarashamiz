"""Diagnostika: qaysi muhit o'zgaruvchilari o'rnatilgani.

Ochish:  https://<loyiha>.vercel.app/api/check
Hech qanday maxfiy qiymat ko'rsatilmaydi - faqat bor/yo'q.
"""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        redis_url = os.environ.get("REDIS_URL") or ""
        scheme = redis_url.split("://")[0] + "://" if "://" in redis_url else None

        info = {
            "BOT_TOKEN": bool(os.environ.get("BOT_TOKEN")),
            "REDIS_URL": bool(redis_url),
            "REDIS_URL_scheme": scheme,
            "WEBAPP_URL": os.environ.get("WEBAPP_URL") or None,
            "APP_URL": os.environ.get("APP_URL") or None,
            "VERCEL_PROJECT_PRODUCTION_URL": os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or None,
            "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
            "ADMIN_ID": os.environ.get("ADMIN_ID") or None,
            "SETUP_KEY": bool(os.environ.get("SETUP_KEY")),
            "CRON_SECRET": bool(os.environ.get("CRON_SECRET")),
            "PRICE_MONTH": os.environ.get("PRICE_MONTH") or "50 (standart)",
            "PRICE_YEAR": os.environ.get("PRICE_YEAR") or "500 (standart)",
            "PRICE_GIFT": os.environ.get("PRICE_GIFT") or "80 (standart)",
            "request_host": self.headers.get("host"),
        }
        token = os.environ.get("BOT_TOKEN") or ""
        info["token_bot_id"] = token.split(":", 1)[0] if ":" in token else None
        info["token_len"] = len(token)

        # Muammolarni aniqlash
        warn = []
        if not info["BOT_TOKEN"]:
            warn.append("BOT_TOKEN yo'q - bot ishlamaydi")
        if not info["REDIS_URL"]:
            warn.append("REDIS_URL yo'q - ma'lumotlar saqlanmaydi va bot yiqiladi")
        elif scheme not in ("redis://", "rediss://"):
            warn.append(f"REDIS_URL '{scheme}' bilan boshlanadi - 'rediss://' kerak "
                        "(REST manzil EMAS!)")
        elif scheme == "redis://" and ".upstash.io" in redis_url:
            warn.append("REDIS_URL 'redis://' (bitta 's'), lekin Upstash TLS talab "
                        "qiladi -> 'rediss://' qiling ('s' qo'shing)")
        if not info["WEBAPP_URL"] and not info["VERCEL_PROJECT_PRODUCTION_URL"]:
            warn.append("WEBAPP_URL yo'q - Mini App manzili aniqlanmaydi")
        info["warnings"] = warn
        info["ok"] = not warn

        # Oxirgi webhook xatosi (?err=1)
        if "err" in (self.path or ""):
            try:
                import redis as _r2
                rc2 = _r2.from_url(os.environ.get("REDIS_URL") or "",
                                   socket_timeout=5, decode_responses=True)
                info["last_error"] = rc2.get("ybot:lasterror")
                info["last_update"] = rc2.get("ybot:lastupdate")
            except Exception as e:  # noqa: BLE001
                info["last_error"] = repr(e)

        # Bot va webhook tirikligini tekshirish (?bot=1)
        # Bu Mini App "auth" xatosining sababini darhol ko'rsatadi:
        # token haqiqiy emas / webhook boshqa domenga ketgan / xato bor.
        if "bot=1" in (self.path or ""):
            try:
                base = "https://api.telegram.org/bot" + token
                with urllib.request.urlopen(base + "/getMe", timeout=8) as r:
                    me = json.loads(r.read())
                res = me.get("result") or {}
                info["getMe"] = {"ok": bool(me.get("ok")),
                                 "id": res.get("id"),
                                 "username": res.get("username"),
                                 "error": None if me.get("ok") else me.get("description")}
                with urllib.request.urlopen(base + "/getWebhookInfo", timeout=8) as r:
                    wh = json.loads(r.read()).get("result") or {}
                info["webhook"] = {k: wh.get(k) for k in (
                    "url", "pending_update_count", "last_error_message",
                    "last_error_date", "max_connections")}
                info["webhook_ok"] = bool(wh.get("url")) and not wh.get("last_error_message")
            except Exception as e:  # noqa: BLE001
                info["getMe"] = {"ok": False, "error": repr(e)}
                info["webhook_ok"] = False

        # Redis kechikishini olchash (?ping=1)
        if "ping" in (self.path or ""):
            try:
                import time as _t
                import redis as _r
                url = os.environ.get("REDIS_URL") or ""
                t0 = _t.time()
                rc = _r.from_url(url, socket_timeout=10, decode_responses=True)
                rc.ping()
                first = round((_t.time() - t0) * 1000)
                times = []
                for _ in range(3):
                    t1 = _t.time()
                    rc.ping()
                    times.append(round((_t.time() - t1) * 1000))
                info["redis_ms"] = {"connect_first": first, "ping": times}
            except Exception as e:  # noqa: BLE001
                info["redis_ms"] = {"error": repr(e)}

        body = json.dumps(info, ensure_ascii=False, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        self.do_GET()

    def log_message(self, *args) -> None:
        pass
