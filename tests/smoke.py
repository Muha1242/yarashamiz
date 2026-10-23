"""Yarashamiz — offline smoke test.

Tashqi xizmatsiz (fakeredis bilan) asosiy mantiqni tekshiradi:
xatlar, kunlik limit, o'yin savollari, juftlik, ball va eslatmalar.

Ishlatish:
    pip install -r requirements.txt fakeredis
    python tests/smoke.py
"""
import asyncio
import datetime as dt
import json
import os
import sys
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import fakeredis  # noqa: E402
import redis  # noqa: E402
import redis.asyncio  # noqa: E402

SERVER = fakeredis.FakeServer()
redis.from_url = lambda *a, **k: fakeredis.FakeRedis(server=SERVER, decode_responses=True)
redis.asyncio.Redis.from_url = lambda *a, **k: fakeredis.aioredis.FakeRedis(
    server=SERVER, decode_responses=True)

os.environ.setdefault("REDIS_URL", "redis://fake:6379/0")
os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("WEBAPP_URL", "https://example.com/mini_app")

import store as st  # noqa: E402
import bot as core  # noqa: E402
from api import app as api_app  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    if cond:
        print(f"✅ {name}")
    else:
        print(f"❌ {name} {extra}")
        FAILS.append(name)


SENT = []


async def fake_send(chat_id, text, **kw):
    SENT.append((chat_id, text))


core.bot.send_message = fake_send


class FakeMsg:
    def __init__(self, uid, data=None, text=None):
        self.from_user = types.SimpleNamespace(id=uid)
        self.web_app_data = (types.SimpleNamespace(data=json.dumps(data))
                             if data is not None else None)
        self.text = text
        self.answers = []

    async def answer(self, text, **kw):
        self.answers.append(text)


class FakeState:
    def __init__(self, cur=None):
        self.cur = cur

    async def get_state(self):
        return self.cur


# ------------------------------- 1. XATLAR -------------------------------
lid = st.add_letter(101, "Salom, kechir meni", ["Kofe ichamiz"], "classic")
check("xat yaratildi", st.letter(lid)["text"] == "Salom, kechir meni")
check("bo'sh id -> None", st.letter(None) is None and st.letter("") is None)
check("bugungi xatlar = 1", st.count_today_letters(101, 0) == 1)
st.add_letter(101, "Yana bir xat", ["Sayr qilamiz"], "love")
check("bugungi xatlar = 2", st.count_today_letters(101, 0) == 2)
check("kelajakdagi chegara -> 0", st.count_today_letters(101, time.time() + 10) == 0)

# o'chib ketgan xat (setda id bor, hash yo'q) crash qilmasligi kerak
st.r.sadd("mine:101", 987654)
check("buzilgan yozuv library'ni yiqitmaydi", len(st.my_library(101)) == 2)
check("buzilgan yozuv limitni yiqitmaydi", st.count_today_letters(101, 0) == 2)
st.r.srem("mine:101", 987654)

# ------------------------------- 2. JUFTLIK ------------------------------
st.add_pair(101, 102)
p = st.pair_of(101)
check("juftlik topildi", p is not None and st.other(p, 101) == 102
      and st.other(p, 102) == 101)

# --------------------------- 3. O'YIN SAVOLLARI --------------------------
games = {g["id"]: g for g in api_app._games(101)["games"]}
check("ilova ab savollari bot bilan bir xil",
      games["ab"]["qs"] == [list(core.AB[core.qidx("ab", k)]) for k in range(5)])
check("ilova wh savollari bot bilan bir xil",
      games["wh"]["qs"] == [core.WHO[core.qidx("wh", k)] for k in range(5)])
check("ilova qz savollari bot bilan bir xil",
      games["qz"]["qs"] == [core.QZ[core.qidx("qz", k)] for k in range(6)])
check("ilova missiyasi bot bilan bir xil", games["ms"]["qs"] == [core.mission_of_day()])

# ------------------------------ 4. MAXFIYLIK -----------------------------
check("begona xatni o'qib bo'lmaydi",
      api_app._letter(103, {"l": lid}) == {"ok": False, "err": "not_yours"})
check("egasi xatni o'qiydi", api_app._letter(101, {"l": lid})["ok"])
check("mavjud bo'lmagan xat -> none",
      api_app._letter(999, {"l": 999999}) == {"ok": False, "err": "none"})

# --------------------------- 5. "YARASHAMIZ" -----------------------------
st.add_pair(202, 203)      # 202 allaqachon juftlikda
l1 = st.add_letter(201, "Kechir", ["Kino"], "classic")
m = FakeMsg(202, {"a": "yes", "l": l1, "o": "Kino"})
SENT.clear()
asyncio.run(core.reply(m))
check("juftlikda bo'lgan odam qayta juftlanmaydi",
      any("allaqachon" in x for x in m.answers), m.answers)
check("xat qabul qiluvchisi o'zgarmadi", st.letter(l1)["receiver"] == 0)
check("yuboruvchi ham juftlanmadi", st.pair_of(201) is None)

l2 = st.add_letter(301, "Yarashamizmi?", ["Sayr"], "love")
m2 = FakeMsg(302, {"a": "yes", "l": l2, "o": "Sayr"})
asyncio.run(core.reply(m2))
check("erkin foydalanuvchi juftlashdi", st.pair_of(302) is not None
      and st.pair_of(301) is not None)
check("xat qabul qiluvchisi yozildi", st.letter(l2)["receiver"] == 302)

m3 = FakeMsg(303, {"a": "yes", "l": l2, "o": "Sayr"})
asyncio.run(core.reply(m3))
check("qabul qilingan xatni boshqa odam olmaydi",
      any("allaqachon" in x for x in m3.answers), m3.answers)

# ------------------------------ 6. BALL ----------------------------------
st.add_pair(401, 402)
pid = st.pair_of(401)[0]
answers = [0, 1, 0, 1, 0]
st.put(pid, "wh", 401, answers)
st.put(pid, "wh", 402, answers)
asyncio.run(core.after(401, st.pair_of(401), "wh"))
first = st.get_pts(pid)
asyncio.run(core.after(402, st.pair_of(402), "wh"))
check("ball qo'shildi", first > 0, first)
check("ball ikki marta qo'shilmaydi", st.get_pts(pid) == first, st.get_pts(pid))

# ------------------------- 7. ESLATMALAR (VAQT) --------------------------
st.add_pair(501, 502)
st.touch(501)
st.touch(502)
st.now = lambda: dt.datetime(2026, 10, 23, 20, 0)      # 20:00 Toshkent
msgs = asyncio.run(core.run_reminders())
check("20:00 da missiya eslatmasi yuboriladi",
      any(u == 501 and "missiya" in txt for u, txt in msgs),
      [(u, t[:30]) for u, t in msgs])
check("20:00 da kunlik savol yuboriladi",
      any(u == 501 and "savol" in txt for u, txt in msgs))
msgs2 = asyncio.run(core.run_reminders())
check("eslatma ikki marta yuborilmaydi",
      all(u != 501 or "missiya" not in txt for u, txt in msgs2))

# --------------------------- 8. XATO HANDLERI ----------------------------
SENT.clear()
st.r.delete("ybot:lasterror")
ev = types.SimpleNamespace(
    exception=ValueError("secret-internal-detail"),
    update=types.SimpleNamespace(
        message=types.SimpleNamespace(from_user=types.SimpleNamespace(id=601)),
        callback_query=None))
asyncio.run(core.on_error(ev))
check("foydalanuvchiga ichki xato ko'rinmaydi",
      bool(SENT) and "secret-internal-detail" not in SENT[0][1], SENT)
check("xato Redis'ga yozildi", "ValueError" in (st.r.get("ybot:lasterror") or ""))

# ----------------------------- 9. ZAXIRA ---------------------------------
m4 = FakeMsg(701, text="assalomu alaykum")
asyncio.run(core.fallback(m4, FakeState()))
check("notanish matnga javob beriladi", bool(m4.answers), m4.answers)
m5 = FakeMsg(702, text="salom")
asyncio.run(core.fallback(m5, FakeState("WritingState:text")))
check("holatda bo'lsa yo'l ko'rsatiladi", bool(m5.answers) and "/cancel" in m5.answers[0])

# ----------------------------- 10. SOVG'A --------------------------------
token = st.make_gift(30)
check("sovg'a ishlatildi", st.use_gift(token, 801) == 30 and st.is_prem(801))
check("sovg'a qayta ishlatilmaydi", st.use_gift(token, 802) == 0 and not st.is_prem(802))

# --------------------------- 11. WEBAPP YO'Q -----------------------------
saved = core.URL
core.URL = ""
check("URL bo'lmasa tugma yasalmaydi", core.main_kb() is None)

# ---------------------- 12. XAT YOZISH OQIMI (FSM) -----------------------
from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.storage.base import StorageKey  # noqa: E402


class FakeOut(FakeMsg):
    async def edit_text(self, text=None, **kw):
        self.answers.append(text)

    async def edit_reply_markup(self, **kw):
        pass


class FakeCb:
    def __init__(self, uid, data, msg):
        self.from_user = types.SimpleNamespace(id=uid)
        self.data = data
        self.message = msg
        self.alerts = []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append(text)


async def _fake_get_me():
    return types.SimpleNamespace(username="testbot")


core.bot.get_me = _fake_get_me
core.URL = saved


async def flow():
    key = StorageKey(bot_id=123456, chat_id=9001, user_id=9001)
    ctx = FSMContext(storage=core.dp.storage, key=key)
    out = FakeOut(9001)
    out.from_user = types.SimpleNamespace(id=9001)
    await core.do_new(out, ctx)
    in_text = (await ctx.get_state() or "")
    assert in_text.endswith("text"), in_text
    out.text = "Kechir meni, xato qildim"
    await core.got_text(out, ctx)
    assert (await ctx.get_state() or "").endswith("offers")
    await core.toggle(FakeCb(9001, "o:0", out), ctx)
    await core.finish(FakeCb(9001, "done", out), ctx)
    assert (await ctx.get_state() or "").endswith("theme")
    bad = FakeCb(9001, "th:night", out)          # premium shablon
    await core.theme(bad, ctx)
    assert any("premium" in (a or "") for a in bad.alerts), bad.alerts
    await core.theme(FakeCb(9001, "th:classic", out), ctx)
    assert await ctx.get_state() is None
    letters = st.my_library(9001)
    assert letters and letters[0]["text"] == "Kechir meni, xato qildim"
    assert any("start=l_" in (s or "") for s in out.answers), out.answers[-2:]


asyncio.run(flow())
check("xat yozish oqimi (FSM) ishlaydi", True)

# kunlik limit
for i in range(core.DAILY_LIMIT):
    st.add_letter(9002, f"xat {i}", ["Kino"], "classic")
out2 = FakeOut(9002)
asyncio.run(core.do_new(out2, FSMContext(
    storage=core.dp.storage,
    key=StorageKey(bot_id=123456, chat_id=9002, user_id=9002))))
check("bepul limit ishlaydi", any("limit" in (a or "") for a in out2.answers),
      out2.answers)

# -------------------- 13. HAVOLA ORQALI XAT OCHISH -----------------------
l3 = st.add_letter(9101, "Seni sog'indim", ["Kofe"], "love")
from aiogram.filters import CommandObject  # noqa: E402

own = FakeOut(9101)
asyncio.run(core.start(own, CommandObject(prefix="/", command="start", args=f"l_{l3}"),
                       FSMContext(storage=core.dp.storage,
                                  key=StorageKey(bot_id=123456, chat_id=9101, user_id=9101))))
check("o'z havolasini ochsa ogohlantiriladi",
      any("sizning xatingiz" in (a or "") for a in own.answers), own.answers)


# --------------------- 14. MINI APP AUTENTIFIKATSIYASI --------------------
import hashlib  # noqa: E402
import hmac  # noqa: E402
import urllib.parse  # noqa: E402


def make_init(uid=555, ts=None):
    p = {"auth_date": str(ts or int(time.time())),
         "query_id": "AAE-test",
         "user": json.dumps({"id": uid, "first_name": "Test"}, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(p.items()))
    secret = hmac.new(b"WebAppData", core.TOKEN.encode(), hashlib.sha256).digest()
    p["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(p)


init = make_init()
check("to'g'ri initData qabul qilinadi",
      (api_app.verify(init) or {}).get("id") == 555)
check("buzilgan initData rad etiladi", api_app.verify(init[:-4] + "0000") is None)
check("hash'siz initData rad etiladi", api_app.verify("user=%7B%7D") is None)
check("eskirgan initData rad etiladi",
      api_app.verify(make_init(ts=int(time.time()) - 10 * 86400)) is None)


print()
if FAILS:
    print(f"❌ {len(FAILS)} ta tekshiruv yiqildi: {FAILS}")
    sys.exit(1)
print("✅ Barcha tekshiruvlar o'tdi")