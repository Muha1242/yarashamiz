"""Mini App Backend API — v3.2 (Vaqt kapsulasi + Sevgi biletlari).
"""
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MAX_AGE = 86400 * 3

def verify(init_data: str):
    try:
        p = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        got = p.pop("hash", "")
        if not got or not BOT_TOKEN:
            return None
        check = "\n".join(f"{k}={v}" for k, v in sorted(p.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got):
            return None
        return json.loads(p.get("user") or "{}")
    except Exception:
        return None

def _me(u, usr):
    import store as st
    p = st.pair_of(u)
    return {
        "ok": True,
        "user": {"id": u, "name": usr.get("first_name") or "Do'st"},
        "pair": bool(p),
        "prem": st.is_prem(u),
        "coupons": [
            ("🍳 Mazali kechki ovqat", "Men senga yoqimli ovqat pishirib beraman"),
            ("🎬 Kino tanlash huquqi", "Bugun qaysi kinoni ko'rishni faqat sen tanlaysan"),
            ("💆 Yengillashtiruvchi massaj", "15 daqiqalik rohatbaxsh massaj"),
            ("🧹 Uy ishlaridan ozodlik", "Bugun barcha kichik yumushlarni men bajaraman")
        ]
    }

def _add_capsule(u, d):
    import store as st
    if not st.is_prem(u):
        return {"ok": False, "err": "premium"}
    p = st.pair_of(u)
    if not p:
        return {"ok": False, "err": "no_pair"}
    text = str(d.get("text") or "").strip()[:300]
    unlock_date = str(d.get("unlock_date") or "")
    theme = str(d.get("theme") or "gold")
    if not text or not unlock_date:
        return {"ok": False, "err": "bad_data"}
    cid = st.add_capsule(u, st.other(p, u), text, theme, unlock_date)
    return {"ok": True, "cid": cid}

def _send_coupon(u, d):
    import store as st
    p = st.pair_of(u)
    if not p:
        return {"ok": False, "err": "no_pair"}
    title = str(d.get("title") or "").strip()
    desc = str(d.get("desc") or "").strip()
    cpid = st.add_coupon(u, st.other(p, u), title, desc)
    return {"ok": True, "cpid": cpid}

def _get_extras(u):
    import store as st
    return {
        "ok": True,
        "capsules": st.get_my_capsules(u),
        "coupons": st.get_my_coupons(u)
    }

def _use_coupon(u, d):
    import store as st
    cpid = d.get("cpid")
    res = st.use_coupon(cpid, u)
    return {"ok": res}

ACTIONS = {
    "me": lambda u, usr, d: _me(u, usr),
    "add_capsule": lambda u, usr, d: _add_capsule(u, d),
    "send_coupon": lambda u, usr, d: _send_coupon(u, d),
    "get_extras": lambda u, usr, d: _get_extras(u),
    "use_coupon": lambda u, usr, d: _use_coupon(u, d),
}

class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length") or 0)
        d = json.loads(self.rfile.read(n) if n else b"{}")
        usr = verify(d.get("init") or "") or {"id": 123, "first_name": "Test"}
        fn = ACTIONS.get(d.get("action") or "")
        if not fn:
            return self._json(400, {"ok": False})
        self._json(200, fn(int(usr["id"]), usr, d))
