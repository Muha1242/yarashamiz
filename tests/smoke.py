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
check("buzilgan id crash qilmaydi", st.letter("abc") is None and st.letter("-5") is None)
check("imzosiz havola rad etiladi",
      st.letter_by_code(str(lid)) is None and st.letter_by_code("") is None)
check("imzolangan havola ishlaydi",
      (st.letter_by_code(st.link_code(lid)) or {}).get("id") == lid)
check("boshqa xat kodi mos kelmaydi", st.code_ok(lid, st.link_code(lid + 1)) is False)
_code = st.link_code(lid)
check("havola kodi Telegram alfavitida",
      len(_code) <= 64 and all(c.isalnum() or c in "_-" for c in _code), _code)
check("non-ASCII imzo crash qilmaydi",
      st.lid_from_code("1_ñ") is None and st.code_ok(lid, "1_ñ") is False)
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
m = FakeMsg(202, {"a": "yes", "l": l1, "o": "Kino", "k": st.link_code(l1)})
SENT.clear()
asyncio.run(core.reply(m))
check("juftlikda bo'lgan odam qayta juftlanmaydi",
      any("allaqachon" in x for x in m.answers), m.answers)
check("xat qabul qiluvchisi o'zgarmadi", st.letter(l1)["receiver"] == 0)
check("yuboruvchi ham juftlanmadi", st.pair_of(201) is None)

l2 = st.add_letter(301, "Yarashamizmi?", ["Sayr"], "love")
m2 = FakeMsg(302, {"a": "yes", "l": l2, "o": "Sayr", "k": st.link_code(l2)})
asyncio.run(core.reply(m2))
check("erkin foydalanuvchi juftlashdi", st.pair_of(302) is not None
      and st.pair_of(301) is not None)
check("xat qabul qiluvchisi yozildi", st.letter(l2)["receiver"] == 302)

m3 = FakeMsg(303, {"a": "yes", "l": l2, "o": "Sayr", "k": st.link_code(l2)})
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
      any(u == 501 and "missiya" in txt for u, txt, _k in msgs),
      [(u, t[:30]) for u, t, _k in msgs])
check("20:00 da kunlik savol yuboriladi",
      any(u == 501 and "savol" in txt for u, txt, _k in msgs))
check("run_reminders o'zi mark qilmaydi", not st.sent(501, "ms"))
for _u, _t, _k in msgs:                 # cron muvaffaqiyatli yuborgandan keyin
    st.mark(_u, _k)
msgs2 = asyncio.run(core.run_reminders())
check("eslatma ikki marta yuborilmaydi",
      all(u != 501 or "missiya" not in txt for u, txt, _k in msgs2))

# o'yin kuni 03:00 da almashadi — 23:59 va 00:01 bir kunga tushadi
st.now = lambda: dt.datetime(2026, 10, 24, 23, 59)
check("o'yin kuni 23:59 da 24-oktabr", st.game_day() == "2026-10-24", st.game_day())
st.now = lambda: dt.datetime(2026, 10, 25, 0, 1)
check("o'yin kuni 00:01 da hali 24-oktabr", st.game_day() == "2026-10-24", st.game_day())
st.add_pair(9801, 9802)
pid_mid = st.pair_of(9801)[0]
st.put(pid_mid, "wh", 9801, [0, 1, 0, 1, 0])
st.now = lambda: dt.datetime(2026, 10, 25, 0, 1)
st.put(pid_mid, "wh", 9802, [0, 1, 0, 1, 0])
check("yarim tundan keyin ham javoblar bir kunda",
      st.done(pid_mid, "wh", 9801) and st.done(pid_mid, "wh", 9802))
asyncio.run(core.after(9802, st.pair_of(9802), "wh"))
check("yarim tundan keyin ball yo'qolmaydi", st.get_pts(pid_mid) == 15,
      st.get_pts(pid_mid))
st.now = lambda: dt.datetime(2026, 10, 25, 3, 1)
check("o'yin kuni 03:01 da yangilanadi", st.game_day() == "2026-10-25", st.game_day())
# keyingi testlar avvalgi vaqtda davom etsin (section 7 shu vaqtni qo'ygan edi)
st.now = lambda: dt.datetime(2026, 10, 23, 20, 0)

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
check("sovg'a TTL oladi", 0 < st.r.ttl(f"gift:{token}") <= 90 * 86400,
      st.r.ttl(f"gift:{token}"))
check("sovg'a ishlatildi", st.use_gift(token, 801) == 30 and st.is_prem(801))
check("sovg'a qayta ishlatilmaydi", st.use_gift(token, 802) == 0 and not st.is_prem(802))
check("yaroqsiz sovg'a -> 0", st.use_gift("yoq-bunday-token", 803) == 0
      and st.use_gift(None, 803) == 0)
old_gift = st.make_gift(30)
st.r.hset(f"gift:{old_gift}", "used", 1)     # deploydan oldin ishlatilgan sovg'a
check("eski ishlatilgan sovg'a qayta berilmaydi",
      st.use_gift(old_gift, 804) == 0 and not st.is_prem(804))

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
    link_txt = [s for s in out.answers if "start=l_" in (s or "")][-1]
    flow_code = link_txt.split("start=l_", 1)[1].strip()
    assert st.letter_by_code(flow_code), flow_code
    kb = core.open_letter_kb(letters[0]["id"], "payload", flow_code)
    url = kb.keyboard[0][0].web_app.url
    assert "&l=" in url and "&k=" + flow_code in url, url


asyncio.run(flow())
check("xat yozish oqimi (FSM) ishlaydi", True)

# /link — eski raqamli havolalar o'rniga yangi imzolangan havola
lc = FakeOut(9001)
asyncio.run(core.link_cmd(lc))
check("link buyrug'i imzolangan havola beradi",
      any("start=l_" in (a or "") for a in lc.answers), lc.answers)
if lc.answers:
    _lc = lc.answers[0].split("start=l_", 1)[-1].split()[0]
    check("link havolasi xatni topadi", bool(st.letter_by_code(_lc)), _lc)

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
asyncio.run(core.start(own, CommandObject(prefix="/", command="start",
                                          args=f"l_{st.link_code(l3)}"),
                       FSMContext(storage=core.dp.storage,
                                  key=StorageKey(bot_id=123456, chat_id=9101, user_id=9101))))
check("o'z havolasini ochsa ogohlantiriladi",
      any("sizning xatingiz" in (a or "") for a in own.answers), own.answers)

# raqamni taxmin qilib (imzosiz) begona xatni ochib bo'lmaydi
guess = FakeOut(9199)
asyncio.run(core.start(guess, CommandObject(prefix="/", command="start", args=f"l_{l3}"),
                       FSMContext(storage=core.dp.storage,
                                  key=StorageKey(bot_id=123456, chat_id=9199, user_id=9199))))
check("imzosiz havola bilan begona xat ochilmaydi",
      any("topilmadi" in (a or "") for a in guess.answers), guess.answers)

# xat havolasini ochish yangi odamni "eski" qilib qo'ymaydi (referral uchun)
st.r.delete("streak:9701")
asyncio.run(core.start(
    FakeOut(9701),
    CommandObject(prefix="/", command="start", args=f"l_{st.link_code(l3)}"),
    FSMContext(storage=core.dp.storage,
               key=StorageKey(bot_id=123456, chat_id=9701, user_id=9701))))
check("xat havolasi referral huquqini yo'qotmaydi",
      not st.r.exists("streak:9701") and not st.r.exists("mine:9701"))

# web_app_data ham imzo talab qiladi (id'ni bilib qo'yib bo'lmaydi)
st.add_pair(9201, 9202)
l_sec = st.add_letter(9201, "Maxfiy xat", ["Kino ko'ramiz"], "classic")
m_nokey = FakeMsg(9202, {"a": "yes", "l": l_sec, "o": "Kino ko'ramiz"})
asyncio.run(core.reply(m_nokey))
check("kod bo'lmasa 'yes' rad etiladi",
      st.letter(l_sec)["receiver"] == 0
      and any("noto'g'ri" in (a or "") for a in m_nokey.answers), m_nokey.answers)

# eski tugma (k'siz) — xatni haqiqatan ko'rgan foydalanuvchi uchun ishlaydi
l_legacy = st.add_letter(9251, "Eski havola", ["Kino ko'ramiz"], "classic")
st.seen(l_legacy, 9252)
m_legacy = FakeMsg(9252, {"a": "yes", "l": l_legacy, "o": "Kino ko'ramiz"})
asyncio.run(core.reply(m_legacy))
check("eski tugma ko'rgan odamda ishlaydi",
      st.letter(l_legacy)["receiver"] == 9252, st.letter(l_legacy))

# imzo to'g'ri bo'lsa ham, taklif matni xatdagi ro'yxatdan tekshiriladi
l_off = st.add_letter(9301, "Kino?", ["Kino ko'ramiz"], "classic")
m_off = FakeMsg(9302, {"a": "yes", "l": l_off, "o": "<b>soxta</b>",
                       "k": st.link_code(l_off)})
SENT.clear()
asyncio.run(core.reply(m_off))
off_msgs = [t for cid, t in SENT if cid == 9301 and "yarashamiz" in t]
check("soxta taklif matni o'tmaydi",
      bool(off_msgs) and "Kino" in off_msgs[0] and "soxta" not in off_msgs[0],
      off_msgs)


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



# ------------------ 15. SHERIK TEKSHIRUVI TOPGAN HOLATLAR -----------------
# (a) chala (maydonlari yo'q) xat crash qilmasligi
st.r.hset("letter:990001", mapping={"sender": 990002})
chala = st.letter(990001)
check("chala xat o'qiladi", bool(chala) and chala["text"] == ""
      and chala["receiver"] == 0 and chala["offers"] == [], chala)

# (b) kunlik limit — mahalliy yarim tun
saved_now = st.now
st.now = lambda: dt.datetime(2026, 10, 24, 0, 10)      # 00:10 Toshkent
start_ts = st.day_start_ts()
# vaqtga bog'liq bo'lmasligi uchun 101 ning boshqa xatlarini kechagi qilamiz
for _x in st.r.smembers("mine:101"):
    st.r.hset(f"letter:{_x}", "ts", start_ts - 60)
st.r.hset(f"letter:{lid}", "ts", start_ts + 60)
check("yarim tundan keyingi xat sanaladi", st.count_today_letters(101, start_ts) == 1)
st.r.hset(f"letter:{lid}", "ts", start_ts - 60)
check("kechagi xat bugungi limitga kirmaydi",
      st.count_today_letters(101, start_ts) == 0)
st.now = saved_now

# (c) "Yarashamiz" ikki marta bosilsa — bitta xabar
st.add_pair(1001, 1002)
l4 = st.add_letter(1001, "Yarashamizmi?", ["Kino"], "classic")
SENT.clear()
first_yes = FakeMsg(1002, {"a": "yes", "l": l4, "o": "Kino", "k": st.link_code(l4)})
asyncio.run(core.reply(first_yes))
second_yes = FakeMsg(1002, {"a": "yes", "l": l4, "o": "Kino", "k": st.link_code(l4)})
asyncio.run(core.reply(second_yes))
sender_msgs = [t for cid, t in SENT if cid == 1001 and "yarashamiz" in t]
check("takroriy 'yes' yuboruvchiga bir marta xabar beradi", len(sender_msgs) == 1,
      sender_msgs)
check("takroriy 'yes' holatni buzmaydi", st.letter(l4)["receiver"] == 1002)
check("takroriy 'yes' qayta javob beradi",
      any("Allaqachon" in (a or "") for a in second_yes.answers), second_yes.answers)

# (d) kunlik savol javobi HTML-escape qilinadi
st.add_pair(1101, 1102)
pid2 = st.pair_of(1101)[0]
st.put(pid2, "kq", 1101, ["<b>salom</b>"])
st.put(pid2, "kq", 1102, ["<script>x</script>"])
SENT.clear()
asyncio.run(core.after(1101, st.pair_of(1101), "kq"))
kq_msgs = [t for cid, t in SENT if "javobi" in t]
check("kunlik savol javobi escape qilinadi",
      bool(kq_msgs) and all("<b>salom</b>" not in t and "<script>" not in t
                            for t in kq_msgs), kq_msgs)
check("escape qilingan matn ko'rinadi",
      any("&lt;b&gt;salom&lt;/b&gt;" in t for t in kq_msgs), kq_msgs)


# ------------------------- 16. REFERRAL TIZIMI ---------------------------
st.add_pair(1202, 1203)
pid_ref = st.pair_of(1202)[0]
pts_before = st.get_pts(pid_ref)
SENT.clear()
asyncio.run(core.start(
    FakeOut(1201),
    CommandObject(prefix="/", command="start", args="ref_1202"),
    FSMContext(storage=core.dp.storage,
               key=StorageKey(bot_id=123456, chat_id=1201, user_id=1201))))
check("referral yozildi", st.r.get("ref:1201") == "1202")
check("referral darhol ball bermaydi", st.get_pts(pid_ref) == pts_before)
check("taklif qiluvchiga xabar ketdi",
      any(cid == 1202 for cid, _ in SENT), SENT)
check("o'zini taklif qilib bo'lmaydi", st.set_ref(1202, 1202) is False)
check("takroriy referral hisoblanmaydi", st.set_ref(1201, 1202) is False)

st.add_letter(1201, "Birinchi xatim", ["Kino"], "classic")
asyncio.run(core.reward_ref(1201))
check("birinchi xatdan keyin +10 ball", st.get_pts(pid_ref) == pts_before + 10,
      st.get_pts(pid_ref))
asyncio.run(core.reward_ref(1201))
check("referral mukofoti bir marta", st.get_pts(pid_ref) == pts_before + 10)
check("referral soni 1", st.refs(1202) == 1 and st.refs_ok(1202) == 1)

st.apply_ref_reward(1202, 3)
check("3 ta taklif -> 7 kun premium", st.is_prem(1202) and st.prem_days(1202) >= 6)
check("referral matni", "ref_1202" in core.invite_text(1202, "testbot"))

# premium fermasi yo'qligi: 10 ta taklif -> 7 + 30 = 37 kun (300 emas)
st.add_pair(2001, 2002)
for i in range(10):
    nu = 3000 + i
    st.set_ref(nu, 2001)
    asyncio.run(core.reward_ref(nu))
farm_days = st.prem_days(2001)
check("10 taklif -> 37 kun (farm yo'q)", 30 <= farm_days <= 37, farm_days)
check("tasdiqlangan takliflar 10", st.refs_ok(2001) == 10, st.refs_ok(2001))

# eski (botni ishlatgan) foydalanuvchi referral bo'la olmaydi
st.add_letter(4001, "eski xat", ["Kino"], "classic")
check("eski foydalanuvchi referral bo'la olmaydi", st.set_ref(4001, 2002) is False)

# juftligi yo'q referrerga ball yo'qolmaydi — juftlik paydo bo'lganda qo'shiladi
st.set_ref(4003, 4002)
asyncio.run(core.reward_ref(4003))
check("juftliksiz referral balli saqlanadi", st.r.get("refball:4002") == "10",
      st.r.get("refball:4002"))
st.add_pair(4002, 4004)
check("juftlik paydo bo'lganda ball qo'shiladi",
      st.get_pts(st.pair_of(4002)[0]) == 10, st.get_pts(st.pair_of(4002)[0]))

# ikkala tomonda ham kutilayotgan ball bo'lsa — ikkalasi bir marta qo'shiladi
st.set_ref(4006, 4005)
asyncio.run(core.reward_ref(4006))
st.set_ref(4008, 4007)
asyncio.run(core.reward_ref(4008))
st.add_pair(4005, 4007)
pid_both = st.pair_of(4005)[0]
check("ikki tomonning ballari qo'shiladi", st.get_pts(pid_both) == 20,
      st.get_pts(pid_both))
st.add_pair(4005, 4007)          # takroriy chaqiruv ballni takrorlamaydi
check("takroriy add_pair ballni takrorlamaydi", st.get_pts(pid_both) == 20,
      st.get_pts(pid_both))

# --------------------- 17. ESLATMA SOZLAMALARI ---------------------------
st.add_pair(1301, 1302)
st.touch(1301)
st.touch(1302)
st.now = lambda: dt.datetime(2026, 10, 23, 20, 0)
st.set_reminders(1301, False)
msgs_off = asyncio.run(core.run_reminders())
check("eslatma o'chirilganda yuborilmaydi",
      all(u != 1301 for u, _t, _k in msgs_off),
      [(u, t[:20]) for u, t, _k in msgs_off])
st.set_reminders(1301, True)
check("eslatma qayta yoqiladi", st.reminders_on(1301) is True)
st.set_reminders(1303, "0")
check("'0' matni -> o'chirilgan", st.reminders_on(1303) is False)
st.set_reminders(1304, "false")
check("'false' matni -> o'chirilgan", st.reminders_on(1304) is False)
st.set_reminders(1305, "1")
check("'1' matni -> yoqilgan", st.reminders_on(1305) is True)

# -------------------- 18. SHIKOYAT / MODERATSIYA -------------------------
before_rep = st.count_reports()
core.ADMIN_ID = "424242"
SENT.clear()
st.add_pair(1401, 1402)
l_report = st.add_letter(1401, "yomon xat", ["Kino"], "classic")
# xatni ko'rmagan odam shikoyat qila olmaydi
m_unseen = FakeMsg(1403, {"a": "report", "l": l_report, "k": st.link_code(l_report)})
asyncio.run(core.reply(m_unseen))
check("ko'rmagan odam shikoyat qila olmaydi",
      any("topilmadi" in (a or "") for a in m_unseen.answers), m_unseen.answers)
st.seen(l_report, 1402)
m_rep = FakeMsg(1402, {"a": "report", "l": l_report, "k": st.link_code(l_report)})
asyncio.run(core.reply(m_rep))
check("shikoyat yozildi", st.count_reports() == before_rep + 1)
check("shikoyat qilgan bloklandi", st.is_blocked(1402, 1401))
check("adminga shikoyat xabari ketdi",
      any(cid == 424242 and "Shikoyat" in txt for cid, txt in SENT), SENT)
check("shikoyatga javob berildi",
      any("Shikoyat qabul" in (a or "") for a in m_rep.answers), m_rep.answers)
# takroriy shikoyat hisoblanmaydi
m_rep2 = FakeMsg(1402, {"a": "report", "l": l_report, "k": st.link_code(l_report)})
asyncio.run(core.reply(m_rep2))
check("takroriy shikoyat hisoblanmaydi", st.count_reports() == before_rep + 1)
check("takroriy shikoyatga javob",
      any("allaqachon" in (a or "") for a in m_rep2.answers), m_rep2.answers)
# bloklangandan keyin javob yuborilmaydi
SENT.clear()
m_blk = FakeMsg(1402, {"a": "reply", "l": l_report, "t": "salom",
                       "k": st.link_code(l_report)})
asyncio.run(core.reply(m_blk))
check("bloklangandan keyin javob ketmaydi",
      not any(cid == 1401 for cid, _ in SENT)
      and any("olmaslik" in (a or "") for a in m_blk.answers), m_blk.answers)
core.ADMIN_ID = ""

# ------------------------- 19. ADMIN ANALITIKA ---------------------------
stats = st.admin_stats()
check("admin: bugungi xatlar", stats["letters_today"] >= 1, stats["letters_today"])
check("admin: bugun faol", stats["active_today"] >= 1, stats["active_today"])
check("admin: yangi foydalanuvchilar", stats["new_today"] >= 1, stats["new_today"])
check("admin: shikoyatlar", stats["reports"] >= 1, stats["reports"])
check("admin: referral", stats["refs"] >= 1, stats["refs"])

# --------------------- 20. ILOVA: REFERRAL / ESLATMA ---------------------
os.environ["BOT_USERNAME"] = "testbot"
me2 = api_app._me(1202, {"first_name": "Ref"})
check("ilova: taklif havolasi", me2["invite"].endswith("start=ref_1202"), me2["invite"])
check("ilova: taklif soni", me2["refs"] == 1 and me2["refsOk"] == 1,
      (me2["refs"], me2["refsOk"]))
check("ilova: eslatma holati", me2["remind"] is True)
check("ilova: eslatmani o'chirish",
      api_app._remind(1202, {"on": False})["remind"] is False
      and st.reminders_on(1202) is False)
api_app._remind(1202, {"on": True})
check("ilova: eslatmani yoqish", st.reminders_on(1202) is True)
check("ilova: 'false' matni o'chiradi",
      api_app._remind(1202, {"on": "false"})["remind"] is False
      and st.reminders_on(1202) is False)
api_app._remind(1202, {"on": True})

# ------------------- 21. ILOVA: QO'SHIMCHA HIMOYA ------------------------
# bepul foydalanuvchi 1 tadan ortiq o'z taklifini server orqali ham qo'sha olmaydi
res_custom = api_app._newletter(
    5001, {"text": "Salom", "offers": [core.OFFERS[0], "A", "B"], "theme": "classic"})
check("bepul: 2 ta o'z taklifi rad etiladi",
      res_custom == {"ok": False, "err": "custom_limit"}, res_custom)

# havola kod bilan yasaladi (raqamni taxmin qilib bo'lmaydi)
st.r.set("ybot:username", "testbot")
api_app._BOTNAME = "testbot"
res_ok = api_app._newletter(
    5002, {"text": "Salom", "offers": [core.OFFERS[0], "A"], "theme": "classic"})
check("bepul: 1 ta o'z taklifi ruxsat", res_ok.get("ok") is True, res_ok)
if res_ok.get("ok"):
    link_code = res_ok["link"].split("start=l_", 1)[1]
    check("ilova havolasi imzolangan",
          (st.letter_by_code(link_code) or {}).get("id") == res_ok["id"])

# juft ismi ilovada ko'rinadi
st.save_name(1203, "Ali")
check("ilova: juft ismi", api_app._me(1202, {"first_name": "Ref"})["partner"] == "Ali")

# sovuq startda taklif havolasi Redis keshidan olinadi
api_app._BOTNAME = None
os.environ.pop("BOT_USERNAME", None)
st.r.set("ybot:username", "cachebot")
me3 = api_app._me(1202, {"first_name": "Ref"})
check("ilova: sovuq startda taklif havolasi",
      "t.me/cachebot?start=ref_1202" in me3["invite"], me3["invite"])

# kelajakdagi auth_date rad etiladi
check("kelajakdagi initData rad etiladi",
      api_app.verify(make_init(ts=int(time.time()) + 3600)) is None)
check("3 soatlik initData rad etiladi (replay oynasi qisqa)",
      api_app.verify(make_init(ts=int(time.time()) - 3 * 3600)) is None)

# --------------------- 22. HTTP HANDLER (do_POST) ------------------------
import io  # noqa: E402


class FakeHTTP:
    """BaseHTTPRequestHandler o'rniga minimal soxta obyekt."""

    def __init__(self, body: bytes, headers=None):
        self.headers = {"Content-Length": str(len(body))}
        if headers:
            self.headers.update(headers)
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.out = None
        self.status = None

    def send_response(self, code):
        self.status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _json(self, code, data):
        self.out = (code, data)
        self.status = code


fh = FakeHTTP(json.dumps({"init": init, "action": "me"}).encode())
api_app.handler.do_POST(fh)
check("HTTP: me -> 200", fh.out and fh.out[0] == 200 and fh.out[1]["ok"], fh.out)
check("HTTP: ism Redis'ga saqlandi", st.r.get("name:555") == "Test",
      st.r.get("name:555"))

fh_bad = FakeHTTP(json.dumps({"init": "user=%7B%7D", "action": "me"}).encode())
api_app.handler.do_POST(fh_bad)
check("HTTP: yaroqsiz init -> 401",
      fh_bad.out and fh_bad.out[0] == 401 and fh_bad.out[1]["err"] == "auth", fh_bad.out)

fh_custom = FakeHTTP(json.dumps({
    "init": init, "action": "newletter", "text": "Salom",
    "offers": [core.OFFERS[0], "A", "B"], "theme": "classic"}).encode())
api_app.handler.do_POST(fh_custom)
check("HTTP: custom_limit qaytadi",
      fh_custom.out and fh_custom.out[1].get("err") == "custom_limit", fh_custom.out)

# ------------------- 23. MINI APP KODINING SINXRONLIGI -------------------
_root = ROOT
for _rel in ("mini_app/app.js", "public/mini_app/app.js"):
    _src = open(os.path.join(_root, _rel), encoding="utf-8").read()
    check(f"{_rel}: havola kodi yuboriladi",
          "const LETTER_KEY" in _src and "k: LETTER_KEY" in _src)
check("mini_app nusxalari bir xil",
      open(os.path.join(_root, "mini_app/app.js"), encoding="utf-8").read() ==
      open(os.path.join(_root, "public/mini_app/app.js"), encoding="utf-8").read())
_js = open(os.path.join(_root, "mini_app/app.js"), encoding="utf-8").read()
check("uzun xat to'liq ko'rsatiladi",
      "letter-full" in _js and "LETTER.t || LETTER.text" in _js)
check("limit tugaganda yaratish tugmasi o'chadi",
      "outOfLimit" in _js and "mk.disabled = outOfLimit" in _js)
check("preview takliflarni yo'qotmaydi", "const sentOffers" in _js)
check("premium kviz oldindan bloklanadi", "kq.locked" in _js)
check("ikki marta yuborish bloklangan", "DATA_SENT" in _js)
check("xato xabarlari aniq", "apiError" in _js)
_html = open(os.path.join(_root, "mini_app/index.html"), encoding="utf-8").read()
check("zoom bloklanmagan", "user-scalable=no" not in _html)
_css = open(os.path.join(_root, "mini_app/style.css"), encoding="utf-8").read()
check("to'liq xat va mobil narx CSS'i",
      ".letter-full" in _css and "@media(max-width:360px)" in _css)
check("mini_app html/css nusxalari bir xil",
      _html == open(os.path.join(_root, "public/mini_app/index.html"),
                    encoding="utf-8").read()
      and _css == open(os.path.join(_root, "public/mini_app/style.css"),
                       encoding="utf-8").read())

# --------------------- 24. WEBAPP_URL NORMALLASHTIRISH -------------------
_saved_webapp = os.environ.get("WEBAPP_URL")
os.environ["WEBAPP_URL"] = "https://demo.vercel.app/mini_app/"
check("WEBAPP_URL /mini_app -> asosiy domen",
      core.base_url() == "https://demo.vercel.app", core.base_url())
check("Mini App URL /mini_app bilan",
      core.app_url() == "https://demo.vercel.app/mini_app", core.app_url())
os.environ["WEBAPP_URL"] = "https://demo.vercel.app"
check("WEBAPP_URL domenda ham Mini App to'g'ri",
      core.app_url() == "https://demo.vercel.app/mini_app", core.app_url())

# ------------------------- 25. SETUP + WEBHOOK ---------------------------
import api.setup as api_setup  # noqa: E402
import api.webhook as api_webhook  # noqa: E402
import api.cron as api_cron  # noqa: E402

_captured = {}


async def _fake_set_webhook(url, **kw):
    _captured.update(url=url, **kw)


async def _fake_get_me():
    return types.SimpleNamespace(username="setupbot")


async def _fake_noop(*a, **kw):
    return None


_saved_bot = (core.bot.set_webhook, core.bot.get_me, core.bot.set_my_commands,
              core.bot.set_my_short_description, core.bot.set_my_description)
os.environ["WEBHOOK_SECRET"] = ""
os.environ["WEBAPP_URL"] = "https://demo.vercel.app/mini_app"
st.r.delete("ybot:webhook_secret")
try:
    core.bot.set_webhook = _fake_set_webhook
    core.bot.get_me = _fake_get_me
    core.bot.set_my_commands = _fake_noop
    core.bot.set_my_short_description = _fake_noop
    core.bot.set_my_description = _fake_noop
    _setup_url = asyncio.run(api_setup._set())
finally:
    (core.bot.set_webhook, core.bot.get_me, core.bot.set_my_commands,
     core.bot.set_my_short_description, core.bot.set_my_description) = _saved_bot
check("setup webhook URL /mini_app ni olib tashlaydi",
      _setup_url == "https://demo.vercel.app/api/webhook", _setup_url)
check("setup webhook secret yaratadi va yuboradi",
      bool(_captured.get("secret_token")) and
      _captured.get("secret_token") == st.r.get("ybot:webhook_secret"),
      _captured.get("secret_token"))

# webhook: token yo'q/noto'g'ri bo'lsa fail closed
api_webhook._SECRET = ""
os.environ.pop("WEBHOOK_SECRET", None)
st.r.delete("ybot:webhook_secret")
fh_wh = FakeHTTP(b"{}")
api_webhook.handler.do_POST(fh_wh)
check("webhook tokensiz -> 401", fh_wh.status == 401, fh_wh.status)
st.r.set("ybot:webhook_secret", "s3cr3t")
check("webhook maxfiy tokenni Redis'dan oladi",
      api_webhook._secret() == "s3cr3t", api_webhook._secret())
fh_wh2 = FakeHTTP(b"{}", {"x-telegram-bot-api-secret-token": "wrong"})
api_webhook.handler.do_POST(fh_wh2)
check("webhook noto'g'ri token -> 401", fh_wh2.status == 401, fh_wh2.status)

# ------------------------ 26. TO'LOV XAVFSIZLIGI -------------------------
class FakeQ:
    def __init__(self, payload, amount=None, currency="XTR", uid=6001):
        self.invoice_payload = payload
        self.total_amount = (core.PRICES["month"] if amount is None else amount)
        self.currency = currency
        self.from_user = types.SimpleNamespace(id=uid)
        self.answers = []

    async def answer(self, ok, error_message=None):
        self.answers.append(ok)


q_ok = FakeQ("prem:month:6001", core.PRICES["month"])
asyncio.run(core.pre(q_ok))
check("to'lov: to'g'ri invoice qabul qilinadi", q_ok.answers == [True], q_ok.answers)
q_bad_amount = FakeQ("prem:month:6001", 1)
asyncio.run(core.pre(q_bad_amount))
check("to'lov: soxta narx rad etiladi", q_bad_amount.answers == [False])
q_bad_uid = FakeQ("prem:month:9999", core.PRICES["month"])
asyncio.run(core.pre(q_bad_uid))
check("to'lov: boshqa odam uid'i rad etiladi", q_bad_uid.answers == [False])
q_bad_cur = FakeQ("prem:month:6001", core.PRICES["month"], currency="USD")
asyncio.run(core.pre(q_bad_cur))
check("to'lov: XTR bo'lmagan valyuta rad etiladi", q_bad_cur.answers == [False])
q_gift = FakeQ("gift:6001", core.PRICES["gift"])
asyncio.run(core.pre(q_gift))
check("to'lov: sovg'a invoice qabul qilinadi", q_gift.answers == [True])


class FakePayMsg:
    def __init__(self, payload, amount, charge, uid=6100, currency="XTR"):
        self.from_user = types.SimpleNamespace(id=uid)
        self.successful_payment = types.SimpleNamespace(
            invoice_payload=payload, total_amount=amount, currency=currency,
            telegram_payment_charge_id=charge)
        self.answers = []

    async def answer(self, text, **kw):
        self.answers.append(text)


st.r.delete("prem:6100")
st.r.delete("pay:chg-ok")
pay1 = FakePayMsg("prem:month:6100", core.PRICES["month"], "chg-ok")
asyncio.run(core.paid(pay1))
_days = st.prem_days(6100)
check("to'lov: premium berildi", _days >= 29 and bool(pay1.answers), _days)
pay2 = FakePayMsg("prem:month:6100", core.PRICES["month"], "chg-ok")
asyncio.run(core.paid(pay2))
check("to'lov replay: ikkinchi marta berilmaydi",
      st.prem_days(6100) == _days and not pay2.answers,
      (st.prem_days(6100), pay2.answers))
pay_bad = FakePayMsg("prem:month:6100", 1, "chg-bad")
asyncio.run(core.paid(pay_bad))
check("to'lov: soxta summa premium bermaydi",
      st.prem_days(6100) == _days and not pay_bad.answers)

# ------------------- 27. KUNLIK LIMIT BYPASS YOPILDI --------------------
_ctx = FSMContext(storage=core.dp.storage,
                  key=StorageKey(bot_id=123456, chat_id=9500, user_id=9500))
asyncio.run(_ctx.set_state(core.W.theme))
asyncio.run(_ctx.update_data(text="Ortiqcha xat", offers=["Kino ko'ramiz"]))
for _i in range(core.DAILY_LIMIT):
    st.add_letter(9500, f"x{_i}", ["Kino ko'ramiz"], "classic")
_cb_limit = FakeCb(9500, "th:classic", FakeOut(9500))
asyncio.run(core.theme(_cb_limit, _ctx))
check("kunlik limit bypass yopildi",
      st.count_letters(9500) == core.DAILY_LIMIT and
      any("limit" in (a or "") for a in _cb_limit.alerts), _cb_limit.alerts)

_ctx2 = FSMContext(storage=core.dp.storage,
                   key=StorageKey(bot_id=123456, chat_id=9501, user_id=9501))
asyncio.run(_ctx2.set_state(core.W.theme))
asyncio.run(_ctx2.update_data(text="Yangi", offers=["Kino ko'ramiz"]))
_cb_theme = FakeCb(9501, "th:__evil__", FakeOut(9501))
asyncio.run(core.theme(_cb_theme, _ctx2))
check("noto'g'ri shablon rad etiladi",
      st.count_letters(9501) == 0 and
      any("Noto'g'ri" in (a or "") for a in _cb_theme.alerts), _cb_theme.alerts)

# ----------------------- 28. QO'SHIMCHA HIMOYA ---------------------------
res_offers = api_app._newletter(
    5200, {"text": "Salom", "offers": core.OFFERS[:9], "theme": "classic"})
check("ilova 9 ta taklifni saqlaydi (jim kesmaydi)",
      bool(res_offers.get("ok")) and
      len(st.letter(res_offers["id"])["offers"]) == 9, res_offers)

# ilova orqali referral mukofoti haqida referrerga xabar boradi
_notes = []
_saved_notify = api_app.notify
api_app.notify = lambda u, t: _notes.append((u, t))
st.set_ref(5400, 1202)
res_ref = api_app._newletter(
    5400, {"text": "Salom", "offers": [core.OFFERS[0]], "theme": "classic"})
api_app.notify = _saved_notify
check("ilova referral xabari yuboriladi",
      bool(res_ref.get("ok")) and any(u == 1202 and "taklif" in t.lower()
                                      for u, t in _notes), _notes)

# retheme faqat xat egasiga va to'g'ri id bilan
_rt = api_app._retheme(101, {"l": str(lid), "theme": "classic"})
check("retheme o'z xatiga ishlaydi", _rt.get("ok") is True, _rt)

check("rate limit ishlaydi",
      st.rate_ok(7001, limit=2, window=60) and
      st.rate_ok(7001, limit=2, window=60) and
      not st.rate_ok(7001, limit=2, window=60))

st.seen(999998, 1)
check("seen kaliti TTL oladi", 0 < st.r.ttl("seen:999998") <= 30 * 86400,
      st.r.ttl("seen:999998"))

fh_big = FakeHTTP(b"x" * (65 * 1024))
api_app.handler.do_POST(fh_big)
check("katta so'rov -> 413", fh_big.status == 413, fh_big.status)

_saved_cron = api_cron.CRON_SECRET
api_cron.CRON_SECRET = ""
fh_cron = FakeHTTP(b"{}")
api_cron.handler._handle(fh_cron)
check("cron secret yo'q -> 503", fh_cron.out and fh_cron.out[0] == 503, fh_cron.out)
api_cron.CRON_SECRET = "s"
fh_cron2 = FakeHTTP(b"{}", {"authorization": "Bearer wrong"})
api_cron.handler._handle(fh_cron2)
check("cron noto'g'ri token -> 401",
      fh_cron2.out and fh_cron2.out[0] == 401, fh_cron2.out)
api_cron.CRON_SECRET = _saved_cron

# WEBAPP_URL ni tiklaymiz
if _saved_webapp is None:
    os.environ.pop("WEBAPP_URL", None)
else:
    os.environ["WEBAPP_URL"] = _saved_webapp

print()
if FAILS:
    print(f"❌ {len(FAILS)} ta tekshiruv yiqildi: {FAILS}")
    sys.exit(1)
print("✅ Barcha tekshiruvlar o'tdi")