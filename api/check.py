"""Diagnostika: qaysi muhit o'zgaruvchilari o'rnatilgani.

Ochish:  https://<loyiha>.vercel.app/api/check
Hech qanday maxfiy qiymat ko'rsatilmaydi - faqat bor/yo'q.
"""
import json
import os
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
        }

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
