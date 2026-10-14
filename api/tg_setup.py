"""Webhook va bot komandalarini o'rnatish (Vercel Python).

Ishlatish:  https://<loyiha>.vercel.app/api/tg_setup
            SETUP_KEY berilgan bo'lsa:  .../api/tg_setup?key=<SETUP_KEY>
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ.get("BOT_TOKEN", "")
SECRET = os.environ.get("WEBHOOK_SECRET", "")
SETUP_KEY = os.environ.get("SETUP_KEY", "")


def app_base() -> str:
    """Ilova manzili: APP_URL -> VERCEL_PROJECT_PRODUCTION_URL -> VERCEL_URL."""
    a = (os.environ.get("APP_URL")
         or os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
         or os.environ.get("VERCEL_URL") or "").strip().rstrip("/")
    if a and not a.lower().startswith("http"):
        a = "https://" + a
    return a


def call(method: str, payload: dict):
    req = urllib.request.Request(
        "https://api.telegram.org/bot" + TOKEN + "/" + method,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if SETUP_KEY and q.get("key", [""])[0] != SETUP_KEY:
            return self._json(403, {"err": "forbidden"})
        if not TOKEN:
            return self._json(400, {"err": "no_bot_token",
                                    "hint": "Vercel'da BOT_TOKEN env o'rnating"})
        app = app_base()
        if not app:
            return self._json(400, {"err": "no_app_url",
                                    "hint": "APP_URL yoki VERCEL_URL kerak"})

        result = {"app": app, "hook": app + "/api/tg"}
        try:
            before = call("getWebhookInfo", {})
            result["before"] = before.get("result")

            hook = {"url": app + "/api/tg",
                    "allowed_updates": ["message", "callback_query",
                                        "pre_checkout_query"]}
            if SECRET:
                hook["secret_token"] = SECRET
            result["webhook"] = call("setWebhook", hook)

            result["commands"] = call("setMyCommands", {"commands": [
                {"command": "start", "description": "Boshlash / bosh menyu"},
                {"command": "menu", "description": "Asosiy menyu"},
                {"command": "help", "description": "Yordam"},
                {"command": "cancel", "description": "Joriy amalni bekor qilish"},
            ]})

            me = call("getMe", {})
            result["bot"] = (me.get("result") or {}).get("username")
            result["ok"] = bool((result["webhook"] or {}).get("ok"))
        except urllib.error.HTTPError as e:
            result["ok"] = False
            result["error"] = e.read().decode(errors="replace")
        except Exception as e:  # noqa: BLE001
            result["ok"] = False
            result["error"] = repr(e)
        self._json(200, result)

    def do_POST(self) -> None:
        self.do_GET()
