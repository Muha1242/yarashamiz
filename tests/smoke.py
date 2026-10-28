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
from api import check as api_check  # noqa: E402

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


async def _fake_get_me():
    return types.SimpleNamespace(username="testbot")


core.bot.get_me = _fake_get_me      # tarmoqqa chiqmaslik uchun erta patch
api_app._notify = lambda *a, **k: None      # testda tarmoqqa chiqmaymiz
api_app._BOTNAME = "testbot"                # bot_username() kesh


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
lid2 = st.add_letter(101, "Yana bir xat", ["Sayr qilamiz"], "love")
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
      any(u == 501 and "missiya" in txt for u, txt, _k in msgs),
      [(u, t[:30]) for u, t, _k in msgs])
check("20:00 da kunlik savol yuboriladi",
      any(u == 501 and "savol" in txt for u, txt, _k in msgs))
# cron kabi: yuborilgandan keyingina belgilaymiz
for u, _txt, k in msgs:
    if k:
        st.mark(u, k)
msgs2 = asyncio.run(core.run_reminders())
check("eslatma ikki marta yuborilmaydi",
      all(u != 501 or "missiya" not in txt for u, txt, _k in msgs2))

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


def make_init(uid=555, ts=None, sig=None, include_sig=False):
    p = {"auth_date": str(ts or int(time.time())),
         "query_id": "AAE-test",
         "user": json.dumps({"id": uid, "first_name": "Test"}, separators=(",", ":"))}
    if sig:
        p["signature"] = sig
    fields = dict(p)
    if sig and not include_sig:
        fields.pop("signature")       # Bot API 8+: signature dcs ga kirmaydi
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", core.TOKEN.encode(), hashlib.sha256).digest()
    p["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(p)


init = make_init()
check("to'g'ri initData qabul qilinadi",
      (api_app.verify(init) or {}).get("id") == 555)
check("buzilgan initData rad etiladi", api_app.verify(init[:-4] + "0000") is None)
check("hash'siz initData rad etiladi", api_app.verify("user=%7B%7D") is None)
check("signature (yangi Bot API) qabul qilinadi",
      (api_app.verify(make_init(sig="AbC123")) or {}).get("id") == 555)
check("signature dcs ichida bo'lgan eski variant ham qabul qilinadi",
      (api_app.verify(make_init(sig="AbC123", include_sig=True)) or {}).get("id") == 555)
check("sabab: bo'sh init -> no_init", api_app.verify_ex("")[1] == "no_init")
check("sabab: buzuq hash", api_app.verify_ex("auth_date=1&hash=deadbeef")[1] == "bad_hash")
check("sabab: eskagan", api_app.verify_ex(
    make_init(ts=int(time.time()) - 10 * 86400))[1] == "expired")
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
st.r.hset(f"letter:{lid2}", "ts", start_ts - 60)       # ikkalasi ham kechagi
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
first_yes = FakeMsg(1002, {"a": "yes", "l": l4, "o": "Kino"})
asyncio.run(core.reply(first_yes))
second_yes = FakeMsg(1002, {"a": "yes", "l": l4, "o": "Kino"})
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

# eski (xat yozgan) foydalanuvchi referral bo'la olmaydi
st.add_letter(4001, "eski xat", ["Kino"], "classic")
check("eski foydalanuvchi referral bo'la olmaydi", st.set_ref(4001, 2002) is False)
# botni ochgan, lekin hali xat yozmagan do'st — taklif qilina oladi
st.touch(4501)
check("botni ochgan do'st taklif bo'ladi", st.set_ref(4501, 2002) is True)

# taklif/shikoyat kalitlarida TTL bor
l_ttl = st.add_letter(4601, "ttl", ["Kino"], "classic")
st.seen(l_ttl, 4602)
check("seen TTL", st.r.ttl(f"seen:{l_ttl}") > 0, st.r.ttl(f"seen:{l_ttl}"))
st.add_report(l_ttl, 4602, 4601, "x")
check("report TTL", st.r.ttl(f"rep:4602:{l_ttl}") > 0,
      st.r.ttl(f"rep:4602:{l_ttl}"))

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
m_unseen = FakeMsg(1403, {"a": "report", "l": l_report})
asyncio.run(core.reply(m_unseen))
check("ko'rmagan odam shikoyat qila olmaydi",
      any("topilmadi" in (a or "") for a in m_unseen.answers), m_unseen.answers)
st.seen(l_report, 1402)
m_rep = FakeMsg(1402, {"a": "report", "l": l_report})
asyncio.run(core.reply(m_rep))
check("shikoyat yozildi", st.count_reports() == before_rep + 1)
check("qabul qilinmagan xatda blok yo'q (begona forward)",
      st.is_blocked(1402, 1401) is False)
check("adminga shikoyat xabari ketdi",
      any(cid == 424242 and "Shikoyat" in txt for cid, txt in SENT), SENT)
check("shikoyatga javob berildi",
      any("tekshiradi" in (a or "") for a in m_rep.answers), m_rep.answers)
# takroriy shikoyat hisoblanmaydi
m_rep2 = FakeMsg(1402, {"a": "report", "l": l_report})
asyncio.run(core.reply(m_rep2))
check("takroriy shikoyat hisoblanmaydi", st.count_reports() == before_rep + 1)
check("takroriy shikoyatga javob",
      any("allaqachon" in (a or "") for a in m_rep2.answers), m_rep2.answers)

# qabul qilingan xat shikoyati -> blok
l_yes = st.add_letter(1401, "yana bir xat", ["Kino"], "classic")
st.seen(l_yes, 1402)
st.set_receiver(l_yes, 1402)
m_rep3 = FakeMsg(1402, {"a": "report", "l": l_yes})
asyncio.run(core.reply(m_rep3))
check("qabul qilingan xatda blok ishlaydi", st.is_blocked(1402, 1401) is True)
check("blok haqida javob",
      any("boshqa xat kelmaydi" in (a or "") for a in m_rep3.answers), m_rep3.answers)

# bloklangandan keyin javob yuborilmaydi
SENT.clear()
m_blk = FakeMsg(1402, {"a": "reply", "l": l_yes, "t": "salom"})
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
st.set_reminders(4701, True)
check("'on' yo'q bo'lsa holat o'zgarmaydi",
      api_app._remind(4701, {})["remind"] is True)
st.set_reminders(4702, False)
check("'on' yo'q bo'lsa o'chirilgan qoladi",
      api_app._remind(4702, {})["remind"] is False)


# ------------------- 21. DIZAYN TIZIMI VA MAVZULAR -----------------------
themes = dict(core.THEMES)
ids = [t for t, _ in core.THEMES]
check("yangi mavzular qo'shilgan",
      {"marmar", "neon", "paper"} <= set(ids), ids)
check("marmar bepul, neon/paper premium",
      "marmar" not in core.PREMIUM_THEMES
      and core.theme_ok("marmar", 99999) is True
      and {"neon", "paper"} <= core.PREMIUM_THEMES
      and core.theme_ok("neon", 99999) is False)
form = api_app._form(101, {})
check("ilova barcha mavzularni ko'rsatadi",
      {t["id"] for t in form["themes"]} == set(ids), len(form["themes"]))
js = open(os.path.join(ROOT, "mini_app/app.js"), encoding="utf-8").read()
css = open(os.path.join(ROOT, "mini_app/style.css"), encoding="utf-8").read()

# har mavzu: nom, PNG rangi, qog'oz va karta uslubi, swatch
missing = [t for t in ids if f"{t}:" not in js]
check("JS: har mavzuda nom va rang bor", not missing, missing)
missing_css = [t for t in ids if t != "classic"
               and (f".pl-inner.theme-{t}" not in css or f".card.theme-{t}" not in css)]
check("CSS: har mavzuda karta va qog'oz uslubi", not missing_css, missing_css)
missing_sw = [t for t in ids if f'.tbtn[data-theme="{t}"]' not in css]
check("CSS: har mavzuda rangli nishon", not missing_sw, missing_sw)
check("yorqin mavzular uchun to'q matn",
      "CARD_INK" in js and "marmar:" in js.split("CARD_INK")[1]
      and "paper:" in js.split("CARD_INK")[1])
check("CSS: reduced-motion qo'llab-quvvatlanadi",
      "prefers-reduced-motion" in css)

# CSS qavslari muvozanati (sintaksis tekshiruvi)
check("CSS qavslari muvozanatli",
      css.count("{") == css.count("}") and css.count("(") == css.count(")"))

# auth xatosi uchun foydalanuvchiga tushunarli karta
check("JS: auth kartasi va 'Botni ochish'",
      "authCard" in js and "Botni ochish" in js and "no_init" in js)
check("JS: har bo'limda auth tekshiruvi",
      js.count("r.err === 'auth'") >= 4 and "f.err === 'auth'" in js)
check("api: GET config bot nomini beradi",
      "def do_GET" in open(os.path.join(ROOT, "api/app.py"), encoding="utf-8").read())
check("check endpoint: bot diagnostikasi (?bot=1)",
      "bot=1" in open(os.path.join(ROOT, "api/check.py"), encoding="utf-8").read())

# ------------------------- 22. VAQT KAPSULASI ----------------------------
check("kapsula premium (bepul uchun yopiq)",
      api_app._capsule_new(99999, {"text": "x", "days": 30})["err"] == "premium")

st.add_prem(7001, 30)
res = api_app._capsule_new(7001, {"text": "Kelajakdagi xat", "days": 30,
                                  "theme": "classic"})
check("kapsula yaratildi", res["ok"] and "start=c_" in res["link"], res)
cid, token = res["id"], res["token"]
check("matn URL'da yo'q", "Kelajakdagi" not in res["link"])

early = api_app._capsule_open(7002, {"t": token})
check("erta ochib bo'lmaydi", early["ok"] and early["locked"] is True
      and "text" not in early, early)

st.r.hset(f"capsule:{cid}", "open_at", int(time.time()) - 5)
opened = api_app._capsule_open(7002, {"t": token})
check("vaqti kelganda ochiladi",
      opened["ok"] and opened.get("text") == "Kelajakdagi xat", opened)
check("qabul qiluvchi yozildi", st.capsule(cid)["receiver"] == 7002)
check("boshqa odam ocholmaydi",
      api_app._capsule_open(7003, {"t": token})["err"] == "not_yours")
check("yuboruvchi o'z kapsulasini ochadi",
      api_app._capsule_open(7001, {"t": token})["ok"] is True)
check("noto'g'ri token", api_app._capsule_open(7001, {"t": "yoq"})["err"] == "none")

# kunlik limit (3 ta)
for i in range(2):
    api_app._capsule_new(7001, {"text": f"x{i}", "days": 30})
check("kapsula kunlik limiti",
      api_app._capsule_new(7001, {"text": "x", "days": 30})["err"] == "limit")

# cron: vaqti kelgan kapsula xabarnomasi (bir marta)
c2 = st.add_capsule(7101, "cron xat", 30)
st.r.hset(f"capsule:{c2[0]}", "open_at", int(time.time()) - 5)
st.r.zadd("caps:due", {str(c2[0]): int(time.time()) - 5})
st.r.hset(f"capsule:{c2[0]}", "receiver", 7102)
msgs_caps = asyncio.run(core.run_reminders())
check("kapsula xabarnomasi yuborildi",
      any(u in (7101, 7102) and "kapsula" in t.lower() for u, t, _k in msgs_caps),
      [(u, t[:24]) for u, t, _k in msgs_caps])
for _u, _t, k in msgs_caps:          # cron kabi: har foydalanuvchi uchun alohida
    if k.startswith("cap:"):
        st.capsule_notified(int(k[4:]), _u)
msgs_caps2 = asyncio.run(core.run_reminders())
check("kapsula xabarnomasi takrorlanmaydi",
      all(u not in (7101, 7102) for u, _t, _k in msgs_caps2))

# qisman yetkazish: sender ketdi, receiver ketmadi -> faqat receiver qayta oladi
c3 = st.add_capsule(7401, "qisman kapsula", 30)
st.r.hset(f"capsule:{c3[0]}", "open_at", int(time.time()) - 5)
st.r.zadd("caps:due", {str(c3[0]): int(time.time()) - 5})
st.r.hset(f"capsule:{c3[0]}", "receiver", 7402)
st.capsule_notified(c3[0], 7401)
check("qisman: sender belgilandi, receiver yo'q",
      st.capsule_is_notified(c3[0], 7401)
      and not st.capsule_is_notified(c3[0], 7402))
kind_c3 = f"cap:{c3[0]}"
msgs_part = asyncio.run(core.run_reminders())
check("qisman: faqat receiver xabari qoldi",
      any(u == 7402 and k == kind_c3 for u, _t, k in msgs_part)
      and not any(u == 7401 and k == kind_c3 for u, _t, k in msgs_part),
      [(u, k) for u, _t, k in msgs_part if k == kind_c3])
st.capsule_notified(c3[0], 7402)
check("ikkalasi belgilangach navbatdan chiqadi",
      st.r.zscore("caps:due", str(c3[0])) is None)

# -------------------------- 23. SEVGI BILETLARI --------------------------
st.add_pair(7201, 7202)
check("juftliksiz bilet yuborilmaydi",
      api_app._coupon_new(7203, {"title": "💆 Massaj"})["err"] == "no_pair")
c_res = api_app._coupon_new(7201, {"title": "🎬 Kino tanlash huquqi"})
check("bilet yuborildi", c_res["ok"], c_res)
coupon_id = c_res["id"]
check("bepul kunlik limit (1 ta)",
      api_app._coupon_new(7201, {"title": "💆 Massaj"})["err"] == "limit")
st.add_prem(7201, 30)
check("premium cheksiz bilet",
      api_app._coupon_new(7201, {"title": "💆 Massaj"})["ok"] is True)
check("yuboruvchi ishlata olmaydi",
      api_app._coupon_use(7201, {"id": coupon_id})["err"] == "not_yours")
check("qabul qiluvchi ishlatadi",
      api_app._coupon_use(7202, {"id": coupon_id})["ok"] is True)
check("bilet ikki marta ishlatilmaydi",
      api_app._coupon_use(7202, {"id": coupon_id})["err"] == "already")
check("bilet holati used", st.coupon(coupon_id)["status"] == "used")
mine = api_app._coupons(7201)
check("biletlar ro'yxati", mine["ok"] and len(mine["coupons"]) >= 2
      and mine["titles"], len(mine["coupons"]))
check("admin: kapsula va biletlar",
      st.admin_stats()["capsules"] >= 3 and st.admin_stats()["coupons"] >= 2)

# ------------------- 24. UI / BOT INTEGRATSIYASI ------------------------
bot_src = open(os.path.join(ROOT, "bot.py"), encoding="utf-8").read()
check("JS: vaqt kapsulasi UI",
      "viewCapsuleOpen" in js and "capsulesSection" in js
      and "capsule_new" in js and "capsule_open" in js)
check("JS: sevgi biletlari UI",
      "couponsSection" in js and "coupon_use" in js and "coupon_new" in js)
check("CSS: kapsula/bilet uslublari",
      ".chip" in css and ".coupon" in css and ".linkbox" in css)
check("bot: kapsula havolasi va cron",
      "start=c_" in bot_src and "due_capsules" in bot_src)
check("bot: biletlar (premium limit)", "COUPON_FREE_PER_DAY" in bot_src)

# ------------------- 25. PRODUCTION TUZATISHLARI -------------------------
saved_url = os.environ.get("WEBAPP_URL")
os.environ["WEBAPP_URL"] = "https://example.vercel.app"
check("WEBAPP_URL domen -> /mini_app", core.app_url().endswith("/mini_app"),
      core.app_url())
os.environ["WEBAPP_URL"] = "https://example.vercel.app/mini_app"
check("WEBAPP_URL to'liq yo'l saqlanadi", core.app_url().endswith("/mini_app"))
os.environ["WEBAPP_URL"] = "example.vercel.app"
check("WEBAPP_URL sxemasiz -> https + /mini_app",
      core.app_url().startswith("https://") and core.app_url().endswith("/mini_app"),
      core.app_url())
os.environ["WEBAPP_URL"] = "https://example.vercel.app/?a=1"
check("WEBAPP_URL query saqlanadi",
      core.app_url() == "https://example.vercel.app/?a=1", core.app_url())
if saved_url is None:
    os.environ.pop("WEBAPP_URL", None)
else:
    os.environ["WEBAPP_URL"] = saved_url

# cron: global rate limiter va cap
import api.cron as api_cron  # noqa: E402
check("cron: global rate limiter (<=30/s)",
      hasattr(api_cron, "_Rate") and 1 <= api_cron.RATE <= 30, api_cron.RATE)
check("cron: MAX_MSGS cap va capped flag",
      api_cron.MAX_MSGS > 0 and "capped" in open(
          os.path.join(ROOT, "api/cron.py"), encoding="utf-8").read())

check("kelajakdagi auth_date rad etiladi",
      api_app.verify_ex(make_init(ts=int(time.time()) + 3600))[1] == "bad_date")

# sender avval ochsa ham partner ocholadi
st.add_prem(7301, 30)
r_s = api_app._capsule_new(7301, {"text": "sender first", "days": 30})
c_s, t_s = r_s["id"], r_s["token"]
st.r.hset(f"capsule:{c_s}", "open_at", int(time.time()) - 5)
check("sender birinchi ochadi", api_app._capsule_open(7301, {"t": t_s})["ok"])
check("sender ochgach partner ham ochadi",
      api_app._capsule_open(7302, {"t": t_s})["ok"] is True
      and st.capsule(c_s)["receiver"] == 7302)

# invite username Redis keshidan (tarmoqsiz)
saved_bu = os.environ.pop("BOT_USERNAME", None)
st.r.set("ybot:username", "redbot")
api_app._BOTNAME = None
check("invite Redis keshidan", "redbot" in api_app.invite_link(101))
api_app._BOTNAME = "testbot"
if saved_bu:
    os.environ["BOT_USERNAME"] = saved_bu

# diagnostika endpointi himoyasi
os.environ["SETUP_KEY"] = "secret123"
check("check: kalitsiz rad etiladi",
      api_check._key_ok("/api/check?bot=1") is False)
check("check: kalit bilan ochiladi",
      api_check._key_ok("/api/check?bot=1&s=secret123") is True)
os.environ.pop("SETUP_KEY", None)
check("check: SETUP_KEY yo'q -> ochiq",
      api_check._key_ok("/api/check?bot=1") is True)




# ------------------- 26. "MESSAGE NOT MODIFIED" HIMOYASI -----------------
from aiogram.exceptions import TelegramBadRequest  # noqa: E402


class _EditMsg:
    def __init__(self, msg):
        self.msg = msg

    async def edit_text(self, *a, **k):
        raise TelegramBadRequest(method=None, message=self.msg)

    async def edit_reply_markup(self, *a, **k):
        raise TelegramBadRequest(method=None, message=self.msg)


asyncio.run(core.safe_edit(
    _EditMsg("Bad Request: message is not modified: specified new message content"),
    "x"))
check("not modified xatosi yutiladi", True)
raised = False
try:
    asyncio.run(core.safe_edit(_EditMsg("Bad Request: message can't be edited"), "x"))
except TelegramBadRequest:
    raised = True
check("boshqa Telegram xatosi ko'tariladi", raised)


print()
if FAILS:
    print(f"❌ {len(FAILS)} ta tekshiruv yiqildi: {FAILS}")
    sys.exit(1)
print("✅ Barcha tekshiruvlar o'tdi")