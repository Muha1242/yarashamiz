"""Upstash Redis REST klienti (faqat Python stdlib) + SQLite blob sinxronizatsiyasi.

Vercel'da fayl tizimi o'qishga mo'ljallangan (faqat /tmp yoziladi va u ham
vaqtinchalik). Shuning uchun SQLite bazasi `bot.db` ni Upstash Redis'ga
base64 blob sifatida saqlaymiz:

    har so'rovda:  Redis -> /tmp/bot.db  (pull)
    so'rov oxirida: /tmp/bot.db -> Redis  (push)

Redis sozlanmagan bo'lsa (lokal ishlash), sinxronizatsiya o'tkazib yuboriladi.
"""
import base64
import json
import os
import urllib.error
import urllib.request

URL = (os.environ.get("UPSTASH_REDIS_REST_URL")
       or os.environ.get("KV_REST_API_URL") or "").rstrip("/")
TOKEN = (os.environ.get("UPSTASH_REDIS_REST_TOKEN")
         or os.environ.get("KV_REST_API_TOKEN") or "")
KEY = os.environ.get("DB_KEY", "yarashamiz:bot.db")

ENABLED = bool(URL and TOKEN)


def _cmd(*parts):
    """Upstash REST API ga bitta buyruq yuboradi."""
    req = urllib.request.Request(
        URL,
        data=json.dumps(list(parts)).encode(),
        headers={"Authorization": "Bearer " + TOKEN,
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("result")


def pull(path):
    """Redis'dagi bazani `path` ga yozadi. Mavjud bo'lmasa False qaytaradi."""
    if not ENABLED:
        return False
    try:
        val = _cmd("GET", KEY)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("[vstore] pull xatosi:", e)
        return False
    if not val:
        return False
    try:
        data = base64.b64decode(val)
    except Exception as e:
        print("[vstore] base64 xatosi:", e)
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def push(path):
    """`path` dagi bazani Redis'ga yozadi."""
    if not ENABLED or not os.path.exists(path):
        return False
    try:
        with open(path, "rb") as f:
            blob = base64.b64encode(f.read()).decode()
        _cmd("SET", KEY, blob)
        return True
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("[vstore] push xatosi:", e)
        return False
