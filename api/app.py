"""Mini App API - to'liq ilova uchun backend.

POST /api/app
{"init": "<telegram initData>", "action": "me" | "library" | "games" | "answer", ...}

initData HMAC-SHA256 bilan tekshiriladi (BOT_TOKEN).
"""
import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MAX_AGE = 86400 * 3          # initData 3 kungacha amal qiladi


def verify(init_data: str):
    """Telegram initData ni tekshiradi. Foydalanuvchi dict yoki None."""
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
        if time.time() - int(p.get("auth_date") or 0) > MAX_AGE:
            return None
        return json.loads(p.get("user") or "{}")
    except Exception:  # noqa: BLE001
        return None


def _me(u, usr):
    import bot as core
    import store as st
    p = st.pair_of(u)
    pts = st.get_pts(p[0]) if p else 0
    days = 0
    partner = None
    if p:
        o = st.other(p, u)
        ts = st.pair_ts(u, o) or 0
        days = max(0, (int(time.time()) - ts) // 86400) if ts else 0
        partner = st.r.get(f"ini:{o}") or st.r.get(f"name:{o}")
    prem = st.is_prem(u)
    return {
        "ok": True,
        "user": {"id": u, "name": usr.get("first_name") or "Do'st",
                 "username": usr.get("username")},
        "pair": bool(p),
        "partner": partner,
        "pts": pts,
        "streak": st.streak(u),
        "prem": prem,
        "premDays": st.prem_days(u) if prem else 0,
        "letters": st.count_letters(u),
        "days": days,
        "prices": core.PRICES,
        "mission": core.dq_of_day(),
        "themeCount": len(core.THEMES),
    }


def _library(u):
    import store as st
    rows = st.my_library(u, 30)
    out = []
    for x in rows:
        out.append({"id": x["id"], "text": x["text"], "theme": x["theme"],
                    "ts": x["ts"], "mine": x["sender"] == u})
    return {"ok": True, "letters": out}


def _games(u):
    import bot as core
    import store as st
    p = st.pair_of(u)
    if not p:
        return {"ok": True, "games": [], "pair": False}
    o = st.other(p, u)
    out = []
    for g, gg in core.GAMES.items():
        item = {"id": g, "name": gg["name"], "mode": gg["mode"], "n": gg["n"],
                "prem": bool(gg.get("prem")), "done": st.done(p[0], g, u),
                "him": st.done(p[0], g, o)}
        if item["prem"] and not st.is_prem(u):
            item["locked"] = True
        if g == "ab":
            item["qs"] = [list(core.AB[core.qidx("ab", k)]) for k in range(gg["n"])]
        elif g == "qz":
            item["qs"] = [core.QZ[core.qidx("qz", k)] for k in range(gg["n"])]
            item["opt"] = ["Ha", "Yo'q"]
        elif g == "wh":
            item["qs"] = [core.WHO[core.qidx("wh", k)] for k in range(gg["n"])]
            item["opt"] = ["Men", "U"]
        elif g == "ms":
            item["qs"] = [core.mission_of_day()]
        elif g == "kq":
            item["qs"] = [core.dq_of_day()]
        out.append(item)
    return {"ok": True, "pair": True, "games": out, "pts": st.get_pts(p[0])}


def _answer(u, d):
    import bot as core
    import store as st
    g, data = d.get("g"), d.get("data")
    p = st.pair_of(u)
    if not p:
        return {"ok": False, "err": "no_pair"}
    gg = core.GAMES.get(g)
    if not gg:
        return {"ok": False, "err": "bad_game"}
    if gg.get("prem") and not st.is_prem(u):
        return {"ok": False, "err": "premium"}
    if st.done(p[0], g, u):
        return {"ok": False, "err": "already"}
    # --- validatsiya ---
    if g in ("wh", "qz"):
        if not isinstance(data, list) or len(data) != gg["n"] or \
                any(not isinstance(x, int) or x not in (0, 1) for x in data):
            return {"ok": False, "err": "bad_data"}
    elif g == "ab":
        if not isinstance(data, list) or len(data) != gg["n"] or \
                any(not isinstance(x, list) or len(x) != 2 or
                    any(not isinstance(v, int) or v not in (0, 1) for v in x) for x in data):
            return {"ok": False, "err": "bad_data"}
    elif g == "kq":
        if not isinstance(data, list) or not data or not str(data[0]).strip():
            return {"ok": False, "err": "bad_data"}
        data = [str(data[0]).strip()[:250]]
    else:  # ms
        data = {"ok": 1}

    st.touch(u)
    st.put(p[0], g, u, data)

    # --- ikkalasi ham o'ynagan bo'lsa: ball hisoblash ---
    result = None
    if st.done(p[0], g, st.other(p, u)):
        from aiogram.client.session.aiohttp import AiohttpSession
        core.bot.session = AiohttpSession()

        async def go():
            try:
                await core.after(u, p, g)
            finally:
                try:
                    await core.bot.session.close()
                except Exception:
                    pass

        asyncio.run(go())
        result = {"pts": st.get_pts(p[0]), "streak": st.streak(u)}

    return {"ok": True, "waiting": result is None, "result": result,
            "him": st.done(p[0], g, st.other(p, u))}


def _letter(u, d):
    """Xatni ko'rish (faqat egasi yoki qabul qiluvchi)."""
    import bot as core
    import store as st
    lid = d.get("l")
    L = st.letter(lid) if lid else st.last_mine(u)
    if not L:
        return {"ok": False, "err": "none"}
    # maxfiylik: begona xatni id orqali o'qib bo'lmaydi
    if L["sender"] != u and L["receiver"] != u:
        return {"ok": False, "err": "not_yours"}
    valid = dict(core.THEMES)
    return {
        "ok": True, "id": L["id"], "text": L["text"], "offers": L["offers"],
        "theme": L["theme"], "ts": L["ts"], "mine": L["sender"] == u,
        "changesLeft": max(0, st.THEME_LIMIT - int(L.get("thn") or 0)),
        "themes": [{"id": t, "name": n, "prem": t in core.PREMIUM_THEMES,
                    "ok": t not in core.PREMIUM_THEMES or st.is_prem(u)}
                   for t, n in core.THEMES if t in valid],
    }


def _retheme(u, d):
    """Xat dizaynini o'zgartirish (faqat egasi, 3 martagacha)."""
    import bot as core
    import store as st
    lid, theme = d.get("l"), d.get("theme")
    L = st.letter(lid) if lid else None
    if not L:
        return {"ok": False, "err": "none"}
    if L["sender"] != u:
        return {"ok": False, "err": "not_mine"}
    if theme not in dict(core.THEMES):
        return {"ok": False, "err": "bad_theme"}
    if theme in core.PREMIUM_THEMES and not st.is_prem(u):
        return {"ok": False, "err": "premium"}
    n = st.set_theme(lid, theme)
    if n == 0:
        return {"ok": False, "err": "limit"}
    if n < 0:
        return {"ok": False, "err": "none"}
    return {"ok": True, "theme": theme,
            "changesLeft": max(0, st.THEME_LIMIT - n)}


_BOTNAME = None


def bot_username():
    """Bot username (keshda saqlanadi)."""
    global _BOTNAME
    if _BOTNAME:
        return _BOTNAME
    import urllib.request
    try:
        import redis as _r
        rc = _r.from_url(os.environ.get("REDIS_URL") or "", socket_timeout=5,
                         decode_responses=True)
        v = rc.get("ybot:username")
        if v:
            _BOTNAME = v
            return v
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/getMe"
        with urllib.request.urlopen(url, timeout=8) as r:
            u = json.loads(r.read().decode()).get("result", {}).get("username")
        if u:
            _BOTNAME = u
            try:
                rc.set("ybot:username", u)
            except Exception:
                pass
        return u
    except Exception:
        pass
    # zaxira: muhit o'zgaruvchisi
    return os.environ.get("BOT_USERNAME") or None


def _form(u, d):
    """Xat yozish formasi uchun malumot."""
    import bot as core
    import store as st
    prem = st.is_prem(u)
    left = None if prem else max(0, core.DAILY_LIMIT -
                                 st.count_today_letters(u, st.day_start_ts()))
    return {
        "ok": True, "isPrem": prem, "left": left, "limit": core.DAILY_LIMIT,
        "textMax": 300,
        "offers": core.OFFERS,
        "themes": [{"id": t, "name": n, "prem": t in core.PREMIUM_THEMES,
                    "ok": t not in core.PREMIUM_THEMES or prem}
                   for t, n in core.THEMES],
    }


def _newletter(u, d):
    """Mini App dan xat yaratish."""
    import bot as core
    import store as st

    text = str(d.get("text") or "").strip()[:300]
    if not text:
        return {"ok": False, "err": "text"}

    raw = d.get("offers") or []
    offers = []
    if isinstance(raw, list):
        for o in raw[:6]:
            o = str(o).strip()[:40]
            if o and o not in offers:
                offers.append(o)
    if not offers:
        return {"ok": False, "err": "offers"}

    theme = str(d.get("theme") or "classic")
    if theme not in dict(core.THEMES):
        theme = "classic"
    prem = st.is_prem(u)
    if theme in core.PREMIUM_THEMES and not prem:
        return {"ok": False, "err": "premium"}

    if not prem and st.count_today_letters(u, st.day_start_ts()) >= core.DAILY_LIMIT:
        return {"ok": False, "err": "limit", "limit": core.DAILY_LIMIT}

    lid = st.add_letter(u, text, offers, theme)
    st.touch(u)
    uname = bot_username()
    left = None if prem else max(0, core.DAILY_LIMIT -
                                 st.count_today_letters(u, st.day_start_ts()))
    return {"ok": True, "id": lid,
            "link": ("https://t.me/" + uname + "?start=l_" + str(lid)) if uname else "",
            "left": left}


ACTIONS = {"me": lambda u, usr, d: _me(u, usr),
           "library": lambda u, usr, d: _library(u),
           "games": lambda u, usr, d: _games(u),
           "answer": lambda u, usr, d: _answer(u, d),
           "letter": lambda u, usr, d: _letter(u, d),
           "retheme": lambda u, usr, d: _retheme(u, d),
           "form": lambda u, usr, d: _form(u, d),
           "newletter": lambda u, usr, d: _newletter(u, d)}


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._json(204, {})

    def do_GET(self) -> None:
        self._json(200, {"ok": True, "service": "yarashamiz app api"})

    def do_POST(self) -> None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n) if n else b"{}")
        except Exception:  # noqa: BLE001
            return self._json(400, {"ok": False, "err": "bad_json"})

        usr = verify(d.get("init") or "")
        if not usr or not usr.get("id"):
            return self._json(401, {"ok": False, "err": "auth"})

        fn = ACTIONS.get(d.get("action") or "")
        if not fn:
            return self._json(400, {"ok": False, "err": "bad_action"})

        try:
            return self._json(200, fn(int(usr["id"]), usr, d))
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            return self._json(200, {"ok": False, "err": "server"})

    def log_message(self, *args) -> None:
        pass
