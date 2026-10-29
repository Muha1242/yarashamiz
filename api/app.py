"""Mini App API - to'liq ilova uchun backend.

POST /api/app
{"init": "<telegram initData>", "action": "me" | "library" | "games" | "answer", ...}

initData HMAC-SHA256 bilan tekshiriladi (BOT_TOKEN).
"""
import asyncio
import hashlib
import hmac
import html
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


def _dcs(fields: dict) -> str:
    """Telegram data-check-string."""
    return "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))


def verify_ex(init_data: str):
    """initData ni tekshiradi. Qaytaradi: (user | None, sabab).

    sabab: ok / no_init / no_token / no_hash / bad_hash / bad_date /
           expired / no_user / bad_data
    """
    if not init_data:
        return None, "no_init"
    if not BOT_TOKEN:
        return None, "no_token"
    try:
        p = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        got = p.pop("hash", "")
        if not got:
            return None, "no_hash"
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        # Bot API 8+: `signature` ba'zi mijozlarda data-check-string ga
        # kirmaydi — ikkala variantni ham qabul qilamiz (xavfsizlik yo'qolmaydi)
        variants = [p]
        if "signature" in p:
            variants.append({k: v for k, v in p.items() if k != "signature"})
        if not any(
            hmac.compare_digest(
                hmac.new(secret, _dcs(f).encode(), hashlib.sha256).hexdigest(), got)
            for f in variants
        ):
            return None, "bad_hash"
        try:
            auth_date = int(p.get("auth_date") or 0)
        except (TypeError, ValueError):
            return None, "bad_date"
        now = time.time()
        if auth_date > now + 300:        # kelajakdagi sana — qabul qilinmaydi
            return None, "bad_date"
        if now - auth_date > MAX_AGE:
            return None, "expired"
        usr = json.loads(p.get("user") or "{}")
        if not usr.get("id"):
            return None, "no_user"
        return usr, "ok"
    except Exception:  # noqa: BLE001
        return None, "bad_data"


def verify(init_data: str):
    """Telegram initData ni tekshiradi. Foydalanuvchi dict yoki None."""
    return verify_ex(init_data)[0]


def _me(u, usr):
    import bot as core
    import store as st
    ps = st.profile_stats(u)          # 1 pipeline (streak/premium/ball/xat)
    p = ps["pair"]
    days = max(0, (int(time.time()) - ps["since"]) // 86400) if ps["since"] else 0
    partner = None
    if p:
        o = st.other(p, u)
        partner = st.r.get(f"name:{o}")
    prem = ps["prem"]
    return {
        "ok": True,
        "user": {"id": u, "name": usr.get("first_name") or "Do'st",
                 "username": usr.get("username")},
        "pair": bool(p),
        "partner": partner,
        "pts": ps["pts"],
        "streak": ps["streak"],
        "prem": prem,
        "premDays": ps["prem_days"] if prem else 0,
        "letters": ps["letters"] if p else st.count_letters(u),
        "days": days,
        "prices": core.PRICES,
        "mission": core.dq_of_day(),
        "themeCount": len(core.THEMES),
        "refs": st.refs(u),
        "refsOk": st.refs_ok(u),
        "remind": st.reminders_on(u),
        "invite": invite_link(u),
        "mood": st.mood_today(u),
        "partnerMood": (st.mood_today(st.other(p, u)) if p else 0),
        "moodIcons": st.MOOD_ICONS,
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
        elif g == "wyr":
            item["qs"] = [
                [f"{a} yoki {b}?", a, b] for a, b in
                (core.WYR[core.qidx("wyr", k)] for k in range(gg["n"]))
            ]
        elif g == "nhi":
            item["qs"] = [core.NHI[core.qidx("nhi", k)] for k in range(gg["n"])]
            item["opt"] = ["Ha", "Yo'q"]
        elif g == "comp":
            item["qs"] = [core.COMP[core.qidx("comp", k)] for k in range(gg["n"])]
            item["opt"] = ["Ha", "Yo'q"]
        elif g == "fin":
            item["qs"] = [core.fin_of_day()]
        elif g == "ms":
            item["qs"] = [core.mission_of_day()]
        elif g == "td":
            item["qs"] = [core.td_of_day()]
        elif g == "kq":
            item["qs"] = [core.dq_of_day()]
        elif g == "deep":
            item["qs"] = [core.deep_of_day()]
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
    # --- validatsiya (o'yin rejimi bo'yicha) ---
    mode = gg["mode"]
    if mode == "match":
        if not isinstance(data, list) or len(data) != gg["n"] or \
                any(not isinstance(x, int) or x not in (0, 1) for x in data):
            return {"ok": False, "err": "bad_data"}
    elif mode == "guess":
        if not isinstance(data, list) or len(data) != gg["n"] or \
                any(not isinstance(x, list) or len(x) != 2 or
                    any(not isinstance(v, int) or v not in (0, 1) for v in x)
                    for x in data):
            return {"ok": False, "err": "bad_data"}
    elif mode == "talk":
        if not isinstance(data, list) or not data or not str(data[0]).strip():
            return {"ok": False, "err": "bad_data"}
        data = [str(data[0]).strip()[:250]]
    else:  # mission
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


def invite_link(u):
    """Referral havolasi (env/Redis kesh — tarmoqqa chiqmaydi)."""
    name = bot_username()
    if not name:
        return ""
    return f"https://t.me/{name}?start=ref_{u}"


def bot_username():
    """Bot username — faqat kesh/env/Redis (tarmoqqa chiqmaydi).

    Tarmoq chaqiruvi Mini App'ni osiltirib qo'ymasligi uchun olib tashlandi;
    username `/api/setup` paytida Redis'ga yoziladi.
    """
    global _BOTNAME
    if _BOTNAME:
        return _BOTNAME
    env = os.environ.get("BOT_USERNAME") or ""
    if env:
        _BOTNAME = env.lstrip("@")
        return _BOTNAME
    try:
        import redis as _r
        rc = _r.from_url(os.environ.get("REDIS_URL") or "", socket_timeout=3,
                         decode_responses=True)
        v = rc.get("ybot:username")
        if v:
            _BOTNAME = v
            return v
    except Exception:  # noqa: BLE001
        pass
    return ""


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
    st.claim_reward(u)              # claim + ball/premium birga (atomar)
    uname = bot_username()
    left = None if prem else max(0, core.DAILY_LIMIT -
                                 st.count_today_letters(u, st.day_start_ts()))
    return {"ok": True, "id": lid,
            "link": ("https://t.me/" + uname + "?start=l_" + str(lid)) if uname else "",
            "left": left}


def _mood(u, d):
    """Kunlik kayfiyatni belgilash."""
    import store as st
    m = st.set_mood(u, d.get("m"))
    if not m:
        return {"ok": False, "err": "bad_mood"}
    p = st.pair_of(u)
    st.touch(u)
    return {"ok": True, "mood": m,
            "partnerMood": (st.mood_today(st.other(p, u)) if p else 0)}


def _remind(u, d):
    """Eslatmalarni yoqish/o'chirish (parametr yo'q bo'lsa — holatni qaytarish)."""
    import store as st
    if "on" not in d:
        return {"ok": True, "remind": st.reminders_on(u)}
    v = d.get("on")
    on = (v is True or v == 1 or
          (isinstance(v, str) and v.strip().lower() in ("1", "true", "on", "yes")))
    st.set_reminders(u, on)
    return {"ok": True, "remind": on}


def _notify(chat_id, text):
    """Bot orqali best-effort xabar (Mini App API ichidan)."""
    if not chat_id:
        return
    try:
        import bot as core
        from aiogram.client.session.aiohttp import AiohttpSession
        core.bot.session = AiohttpSession()

        async def go():
            try:
                await core.bot.send_message(chat_id, text)
            finally:
                try:
                    await core.bot.session.close()
                except Exception:  # noqa: BLE001
                    pass

        asyncio.run(go())
    except Exception:  # noqa: BLE001
        pass


def _capsules(u):
    """O'z kapsulalari (premium)."""
    import bot as core
    import store as st
    prem = st.is_prem(u)
    now = time.time()
    uname = bot_username() or ""
    rows = []
    for c in st.capsules_of(u)[:30]:
        due = now >= c["open_at"]
        rows.append({
            "id": c["id"], "openAt": c["open_at"], "theme": c["theme"],
            "opened": bool(c["opened"]), "due": bool(due),
            "sent": bool(c["receiver"]),
            "preview": c["text"][:80] if due else "",
            "link": (f"https://t.me/{uname}?start=c_{c['token']}"
                     if uname else ""),
        })
    left = max(0, core.CAPSULE_LIMIT - st.capsules_today(u)) if prem else None
    return {"ok": True, "prem": prem, "capsules": rows,
            "days": [{"label": n, "days": d} for n, d in core.CAPSULE_DAYS],
            "limit": core.CAPSULE_LIMIT, "left": left,
            "maxText": st.CAPSULE_MAX_TEXT,
            "themes": [{"id": t, "name": n, "prem": t in core.PREMIUM_THEMES,
                        "ok": t not in core.PREMIUM_THEMES or prem}
                       for t, n in core.THEMES]}


def _capsule_new(u, d):
    """Vaqt kapsulasi yaratish (faqat premium)."""
    import bot as core
    import store as st
    if not st.is_prem(u):
        return {"ok": False, "err": "premium"}
    text = str(d.get("text") or "").strip()[:st.CAPSULE_MAX_TEXT]
    if not text:
        return {"ok": False, "err": "text"}
    try:
        days = int(d.get("days") or 0)
    except (TypeError, ValueError):
        days = 0
    if days not in {v for _, v in core.CAPSULE_DAYS}:
        return {"ok": False, "err": "days"}
    theme = str(d.get("theme") or "classic")
    if theme not in dict(core.THEMES):
        theme = "classic"
    if theme in core.PREMIUM_THEMES and not st.is_prem(u):
        return {"ok": False, "err": "premium_theme"}
    if st.capsules_today(u) >= core.CAPSULE_LIMIT:
        return {"ok": False, "err": "limit", "limit": core.CAPSULE_LIMIT}
    cid, token, open_at = st.add_capsule(u, text, days, theme)
    uname = bot_username() or ""
    return {"ok": True, "id": cid, "openAt": open_at, "token": token,
            "link": (f"https://t.me/{uname}?start=c_{token}" if uname else ""),
            "left": max(0, core.CAPSULE_LIMIT - st.capsules_today(u))}


def _capsule_open(u, d):
    """Kapsulani ochish (vaqt kelgandagina matn qaytadi)."""
    import store as st
    cid, C = st.capsule_by_token(str(d.get("t") or ""))
    if not C:
        return {"ok": False, "err": "none"}
    c, why = st.open_capsule(cid, u)
    if why == "early":
        return {"ok": True, "locked": True, "openAt": C["open_at"],
                "theme": C["theme"]}
    if why == "not_yours":
        return {"ok": False, "err": "not_yours"}
    if why == "none" or c is None:
        return {"ok": False, "err": "none"}
    return {"ok": True, "locked": False, "text": c["text"], "theme": c["theme"],
            "openAt": c["open_at"], "from": c["sender"],
            "mine": c["sender"] == u}


def _coupons(u):
    import bot as core
    import store as st
    prem = st.is_prem(u)
    rows = [{
        "id": x["id"], "title": x["title"], "status": x["status"],
        "mine": x["from"] == u, "ts": x["ts"], "usedTs": x["used_ts"],
    } for x in st.coupons_of(u)[:40]]
    left = None if prem else max(
        0, core.COUPON_FREE_PER_DAY - st.coupons_sent_today(u))
    return {"ok": True, "coupons": rows, "prem": prem,
            "pair": bool(st.pair_of(u)), "titles": core.COUPON_TITLES,
            "left": left, "freePerDay": core.COUPON_FREE_PER_DAY}


def _coupon_new(u, d):
    import bot as core
    import store as st
    p = st.pair_of(u)
    if not p:
        return {"ok": False, "err": "no_pair"}
    title = str(d.get("title") or "").strip()[:60]
    if not title:
        return {"ok": False, "err": "title"}
    prem = st.is_prem(u)
    if not prem and st.coupons_sent_today(u) >= core.COUPON_FREE_PER_DAY:
        return {"ok": False, "err": "limit", "limit": core.COUPON_FREE_PER_DAY}
    to = st.other(p, u)
    cid = st.add_coupon(u, to, title)
    st.touch(u)
    _notify(to, "🎟️ Sizga sevgi bileti keldi: <b>" + html.escape(title) +
            "</b>\nMini App → «Hisobim» bo'limida ko'ring.")
    left = None if prem else max(
        0, core.COUPON_FREE_PER_DAY - st.coupons_sent_today(u))
    return {"ok": True, "id": cid, "left": left}


def _coupon_use(u, d):
    import store as st
    try:
        cid = int(d.get("id"))
    except (TypeError, ValueError):
        return {"ok": False, "err": "bad_id"}
    c, why = st.use_coupon(cid, u)
    if why == "not_yours":
        return {"ok": False, "err": "not_yours"}
    if why == "already":
        return {"ok": False, "err": "already"}
    if why in ("none", "busy") or c is None:
        return {"ok": False, "err": why or "none"}
    _notify(c["from"], "🎟️ Biletingiz ishlatildi: <b>" +
            html.escape(c["title"]) + "</b>")
    return {"ok": True, "status": "used"}


ACTIONS = {"me": lambda u, usr, d: _me(u, usr),
           "library": lambda u, usr, d: _library(u),
           "games": lambda u, usr, d: _games(u),
           "answer": lambda u, usr, d: _answer(u, d),
           "letter": lambda u, usr, d: _letter(u, d),
           "retheme": lambda u, usr, d: _retheme(u, d),
           "form": lambda u, usr, d: _form(u, d),
           "remind": lambda u, usr, d: _remind(u, d),
           "mood": lambda u, usr, d: _mood(u, d),
           "capsules": lambda u, usr, d: _capsules(u),
           "capsule_new": lambda u, usr, d: _capsule_new(u, d),
           "capsule_open": lambda u, usr, d: _capsule_open(u, d),
           "coupons": lambda u, usr, d: _coupons(u),
           "coupon_new": lambda u, usr, d: _coupon_new(u, d),
           "coupon_use": lambda u, usr, d: _coupon_use(u, d),
           "newletter": lambda u, usr, d: _newletter(u, d)}


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, data: dict) -> None:
        body = b"" if code == 204 else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        if code != 204:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._json(204, {})

    def do_GET(self) -> None:
        try:
            bot = bot_username() or ""
        except Exception:  # noqa: BLE001
            bot = ""
        self._json(200, {"ok": True, "service": "yarashamiz app api",
                         "bot": bot,
                         "webapp": os.environ.get("WEBAPP_URL") or ""})

    def do_POST(self) -> None:
        try:
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n) if n else b"{}")
        except Exception:  # noqa: BLE001
            return self._json(400, {"ok": False, "err": "bad_json"})

        usr, why = verify_ex(d.get("init") or "")
        if not usr or not usr.get("id"):
            # sabab ilovaga qaytariladi (maxfiy ma'lumot yo'q) - foydalanuvchi
            # va admin nima bo'lganini darhol ko'radi
            return self._json(401, {"ok": False, "err": "auth", "why": why,
                                    "bot": bot_username() or ""})

        fn = ACTIONS.get(d.get("action") or "")
        if not fn:
            return self._json(400, {"ok": False, "err": "bad_action"})

        try:
            return self._json(200, fn(int(usr["id"]), usr, d))
        except Exception:  # noqa: BLE001
            tb = traceback.format_exc()
            traceback.print_exc()
            try:
                import redis as _r
                rc = _r.from_url(os.environ.get("REDIS_URL") or "",
                                 socket_timeout=3, decode_responses=True)
                rc.set("ybot:lasterror", (tb or "")[-1500:])
            except Exception:  # noqa: BLE001
                pass
            return self._json(200, {"ok": False, "err": "server"})

    def log_message(self, *args) -> None:
        pass
