"""Kunlik kanal posti — Vercel Cron (`/api/channel`).

Har kuni 09:00 (Toshkent) da `content/channel_posts.json` dan navbatdagi
postni kanalga yuboradi. Dushanba — haftalik post.

Xavfsizlik: `Authorization: Bearer $CRON_SECRET` yoki `?s=CRON_SECRET`.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
SECRET = os.environ.get("CRON_SECRET", "")
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "5"))
CONTENT = os.path.join(ROOT, "content", "channel_posts.json")


def _local_now():
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TZ_OFFSET)


def _load():
    with open(CONTENT, encoding="utf-8") as f:
        return json.load(f)


def _pick(now=None):
    """Bugungi post: (item, kind, index, sana)."""
    now = now or _local_now()
    data = _load()
    ordinal = now.date().toordinal()
    if now.weekday() == 0 and data.get("weekly"):
        pool, kind, idx = data["weekly"], "weekly", (ordinal // 7) % len(data["weekly"])
    else:
        pool, kind, idx = data["daily"], "daily", ordinal % len(data["daily"])
    return pool[idx], kind, idx, now.date().isoformat()


def _api(method, params):
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", data=body)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _post(item):
    if item.get("type") == "poll":
        return _api("sendPoll", {
            "chat_id": CHANNEL_ID,
            "question": str(item.get("text"))[:300],
            "options": json.dumps(item.get("options") or [], ensure_ascii=False),
            "is_anonymous": "true",
        })
    return _api("sendMessage", {
        "chat_id": CHANNEL_ID,
        "text": str(item.get("text") or ""),
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })


def _run(force=False):
    if not BOT_TOKEN or not CHANNEL_ID:
        return {"ok": False, "error": "BOT_TOKEN/CHANNEL_ID yo'q"}
    item, kind, idx, day = _pick()
    key = f"ch:last:{day}"
    try:
        import redis as _r
        rc = _r.from_url(os.environ.get("REDIS_URL") or "", socket_timeout=4,
                         decode_responses=True)
        if not force and not rc.set(key, f"{kind}:{idx}", nx=True, ex=2 * 86400):
            return {"ok": True, "skipped": True, "day": day}
    except Exception:  # noqa: BLE001
        pass
    res = _post(item)
    return {"ok": bool(res.get("ok")), "kind": kind, "index": idx, "day": day,
            "message_id": (res.get("result") or {}).get("message_id"),
            "error": res.get("description")}


def _key_ok(path, headers):
    if not SECRET:
        return False
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(path or "").query)
    if (q.get("s") or [""])[0] == SECRET:
        return True
    return headers.get("authorization") == "Bearer " + SECRET


class handler(BaseHTTPRequestHandler):
    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path or ""
        if not _key_ok(path, self.headers):
            return self._json(401, {"ok": False, "err": "unauthorized"})
        force = "force=1" in path
        try:
            return self._json(200, _run(force=force))
        except Exception as e:  # noqa: BLE001
            return self._json(200, {"ok": False, "error": repr(e)})

    def do_POST(self):
        self.do_GET()

    def log_message(self, *args):
        pass
