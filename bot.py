"""Yarashamiz boti v2: xat + juftlik o'yinlari (A yoki B, Kim ko'proq, Kunlik missiya)."""
import asyncio, base64, datetime as dt, json, os, sqlite3, time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
                           WebAppInfo, InlineKeyboardMarkup as IM, InlineKeyboardButton as IB)

TOKEN, URL = os.environ["BOT_TOKEN"], os.environ["WEBAPP_URL"]
DAILY_LIMIT = 3
OFFERS = ["Birga ovqatlanamiz", "Sayr qilamiz", "Kofe ichamiz", "Kino ko'ramiz"]
AB = [("Kofe yoki choy?", "Kofe", "Choy"), ("Tong yoki tun?", "Tong", "Tun"),
      ("Dengiz yoki tog'?", "Dengiz", "Tog'"), ("Kino yoki sayr?", "Kino", "Sayr"),
      ("Shirin yoki sho'r?", "Shirin", "Sho'r")]
WHO = ["Kim ko'proq kech qoladi?", "Kim birinchi kechirim so'raydi?", "Kim ko'proq gapiradi?",
       "Kim ko'proq uxlaydi?", "Kim yaxshi ovqat pishiradi?"]
MISSIONS = ["Bugun juftingizga 3 ta yaxshi gap ayting.", "Juftingizning eng yaxshi ko'rgan qo'shig'ini qo'yib bering.",
            "Birga o'tgan eng yaxshi kunni eslab yozing.", "Kichik syurpriz qiling: choy yoki shirinlik.",
            "Juftingizdan bugun nima yordam kerakligini so'rang.", "Birga rasmga tushing.",
            "Juftingizga ovozli xabar yuboring."]
NAMES = {"ab": "A yoki B", "wh": "Kim ko'proq?", "ms": "Kunlik missiya"}
bot, dp = Bot(TOKEN), Dispatcher()
db = sqlite3.connect("bot.db")
db.executescript("""
CREATE TABLE IF NOT EXISTS letters(id INTEGER PRIMARY KEY, sender INT, text TEXT, offers TEXT, ts INT);
CREATE TABLE IF NOT EXISTS blocked(user INT, sender INT, PRIMARY KEY(user, sender));
CREATE TABLE IF NOT EXISTS pairs(id INTEGER PRIMARY KEY, a INT, b INT, pts INT DEFAULT 0, UNIQUE(a,b));
CREATE TABLE IF NOT EXISTS ans(pair INT, day TEXT, game TEXT, user INT, data TEXT, PRIMARY KEY(pair,day,game,user));
""")
today = lambda: dt.date.today().isoformat()

def pair_of(u):
    return db.execute("SELECT id,a,b FROM pairs WHERE a=? OR b=? ORDER BY id DESC LIMIT 1", (u, u)).fetchone()
def other(p, u): return p[2] if p[1] == u else p[1]
def get(pid, g, u):
    r = db.execute("SELECT data FROM ans WHERE pair=? AND day=? AND game=? AND user=?", (pid, today(), g, u)).fetchone()
    return json.loads(r[0]) if r else None
def put(pid, g, u, d):
    db.execute("INSERT OR REPLACE INTO ans VALUES(?,?,?,?,?)", (pid, today(), g, u, json.dumps(d))); db.commit()
def done(pid, g, u):
    d = get(pid, g, u)
    return d is not None and (g == "ms" or len(d) >= 5)

def games_view(u):
    p = pair_of(u)
    if not p: return None, None
    o, rows, txt = other(p, u), [], "Bugungi o'yinlar. Ball faqat ikkalangiz ham o'ynasangiz beriladi.\n\n"
    for g in NAMES:
        me, him = done(p[0], g, u), done(p[0], g, o)
        txt += f"{NAMES[g]}: siz {'✅' if me else '⏳'}, juftingiz {'✅' if him else '⏳'}\n"
        if not me: rows.append([IB(text=NAMES[g], callback_data=f"go:{g}")])
    pts = db.execute("SELECT pts FROM pairs WHERE id=?", (p[0],)).fetchone()[0]
    return txt + f"\nJuftlik bali: {pts}", IM(inline_keyboard=rows)

def menu(u):
    rows = [[IB(text="Xat yozish", callback_data="new")]]
    if pair_of(u): rows.append([IB(text="O'yinlar", callback_data="games")])
    return IM(inline_keyboard=rows)

class W(StatesGroup):
    text = State(); offers = State()

@dp.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    arg = command.args or ""
    if arg.startswith("l_"):
        row = db.execute("SELECT sender,text,offers FROM letters WHERE id=?", (arg[2:],)).fetchone()
        if not row: return await m.answer("Xat topilmadi.")
        sender, text, offers = row
        if db.execute("SELECT 1 FROM blocked WHERE user=? AND sender=?", (m.from_user.id, sender)).fetchone():
            return await m.answer("Bu yuboruvchidan xat olmaslikni tanlagansiz.")
        d = base64.urlsafe_b64encode(json.dumps({"t": text, "o": json.loads(offers)}).encode()).decode()
        kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[
            KeyboardButton(text="Xatni ochish", web_app=WebAppInfo(url=f"{URL}?d={d}&l={arg[2:]}"))]])
        return await m.answer("Sizga xat bor", reply_markup=kb)
    await m.answer("Yarashamiz. Arazni xat bilan tugating.", reply_markup=menu(m.from_user.id))

@dp.callback_query(F.data == "new")
async def new(c: CallbackQuery, state: FSMContext):
    n = db.execute("SELECT COUNT(*) FROM letters WHERE sender=? AND ts>?", (c.from_user.id, time.time() - 86400)).fetchone()[0]
    if n >= DAILY_LIMIT: return await c.answer("Bugungi limit tugadi. Ertaga yozing.", show_alert=True)
    await state.set_state(W.text)
    await c.message.answer("Xat matnini yozing (300 belgigacha). Uzr so'rang, samimiy bo'ling.")
    await c.answer()

def offer_kb(sel):
    rows = [[IB(text=("✓ " if o in sel else "") + o, callback_data=f"o:{i}")] for i, o in enumerate(OFFERS)]
    return IM(inline_keyboard=rows + [[IB(text="Tayyor", callback_data="done")]])

@dp.message(W.text, F.text)
async def got_text(m: Message, state: FSMContext):
    await state.update_data(text=m.text[:300], offers=[]); await state.set_state(W.offers)
    await m.answer("Qanday uchrashuv taklif qilasiz? (bir nechtasini tanlang)", reply_markup=offer_kb([]))

@dp.callback_query(W.offers, F.data.startswith("o:"))
async def toggle(c: CallbackQuery, state: FSMContext):
    o = OFFERS[int(c.data[2:])]; sel = (await state.get_data())["offers"]
    sel = [x for x in sel if x != o] if o in sel else sel + [o]
    await state.update_data(offers=sel)
    await c.message.edit_reply_markup(reply_markup=offer_kb(sel)); await c.answer()

@dp.callback_query(W.offers, F.data == "done")
async def finish(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if not d["offers"]: return await c.answer("Kamida bitta taklif tanlang", show_alert=True)
    cur = db.execute("INSERT INTO letters(sender,text,offers,ts) VALUES(?,?,?,?)",
                     (c.from_user.id, d["text"], json.dumps(d["offers"]), int(time.time()))); db.commit()
    me = await bot.get_me(); await state.clear()
    await c.message.answer("Xat tayyor. Havolani juftingizga o'zingiz yuboring:\n"
                           f"https://t.me/{me.username}?start=l_{cur.lastrowid}"); await c.answer()

@dp.message(F.web_app_data)
async def reply(m: Message):
    r = json.loads(m.web_app_data.data)
    row = db.execute("SELECT sender FROM letters WHERE id=?", (r.get("l"),)).fetchone()
    sender = row[0] if row else None
    if r["a"] == "stop" and sender:
        db.execute("INSERT OR IGNORE INTO blocked VALUES(?,?)", (m.from_user.id, sender)); db.commit()
        return await m.answer("Tushunarli. Bu yuboruvchidan boshqa xat kelmaydi.")
    if r["a"] == "yes" and sender:
        db.execute("INSERT OR IGNORE INTO pairs(a,b) VALUES(?,?)", (sender, m.from_user.id)); db.commit()
        await bot.send_message(sender, f"Javob: yarashamiz. Taklif: {r.get('o')}\nEndi birga o'ynashingiz mumkin.", reply_markup=menu(sender))
        return await m.answer("Yarashdingiz. Endi birga o'ynang.", reply_markup=menu(m.from_user.id))
    if r["a"] == "later" and sender:
        await bot.send_message(sender, "Javob: hali tayyor emas, keyinroq.")
    await m.answer("Javobingiz yuborildi.")

@dp.message(Command("games"))
async def games_cmd(m: Message):
    t, kb = games_view(m.from_user.id)
    await m.answer(t or "Avval xat orqali yarashing.", reply_markup=kb)

@dp.callback_query(F.data == "games")
async def games_cb(c: CallbackQuery):
    t, kb = games_view(c.from_user.id); await c.message.answer(t, reply_markup=kb); await c.answer()

def q_ab(i):
    q, a, b = AB[i]; return q, IM(inline_keyboard=[[IB(text=a, callback_data=f"abo:{i}:0"), IB(text=b, callback_data=f"abo:{i}:1")]])

@dp.callback_query(F.data.startswith("go:"))
async def go(c: CallbackQuery):
    g, p = c.data[3:], pair_of(c.from_user.id)
    if not p or done(p[0], g, c.from_user.id): return await c.answer("Bugun o'ynagansiz")
    if g == "ab":
        q, kb = q_ab(len(get(p[0], g, c.from_user.id) or []))
        await c.message.answer("Avval o'zingiz tanlang, keyin juftingiz nimani tanlashini toping.\n\n" + q, reply_markup=kb)
    elif g == "wh":
        await ask_who(c.message, 0)
    else:
        txt = MISSIONS[dt.date.today().toordinal() % len(MISSIONS)]
        await c.message.answer("Bugungi missiya:\n" + txt, reply_markup=IM(inline_keyboard=[[IB(text="Bajardim", callback_data="msd")]]))
    await c.answer()

async def ask_who(msg, i):
    await msg.answer(f"{i+1}/5. {WHO[i]}", reply_markup=IM(inline_keyboard=[[IB(text="Men", callback_data=f"wh:{i}:0"), IB(text="U", callback_data=f"wh:{i}:1")]]))

@dp.callback_query(F.data.startswith("abo:"))
async def ab_own(c: CallbackQuery):
    _, i, o = c.data.split(":"); q, a, b = AB[int(i)]
    await c.message.edit_text(f"{q}\nSiz: {(a, b)[int(o)]}. Juftingiz nimani tanlaydi?",
        reply_markup=IM(inline_keyboard=[[IB(text=a, callback_data=f"abg:{i}:{o}:0"), IB(text=b, callback_data=f"abg:{i}:{o}:1")]]))
    await c.answer()

@dp.callback_query(F.data.startswith("abg:"))
async def ab_guess(c: CallbackQuery):
    _, i, o, g = c.data.split(":"); u, p = c.from_user.id, pair_of(c.from_user.id)
    d = get(p[0], "ab", u) or []
    if len(d) != int(i): return await c.answer()
    d.append([int(o), int(g)]); put(p[0], "ab", u, d)
    if len(d) < 5:
        q, kb = q_ab(len(d)); await c.message.edit_text(q, reply_markup=kb)
    else:
        await c.message.edit_text("Tayyor."); await after(u, p, "ab")
    await c.answer()

@dp.callback_query(F.data.startswith("wh:"))
async def wh(c: CallbackQuery):
    _, i, x = c.data.split(":"); u, p = c.from_user.id, pair_of(c.from_user.id)
    d = get(p[0], "wh", u) or []
    if len(d) != int(i): return await c.answer()
    d.append(u if x == "0" else other(p, u)); put(p[0], "wh", u, d)
    await c.message.delete()
    if len(d) < 5: await ask_who(c.message, len(d))
    else: await c.message.answer("Tayyor."); await after(u, p, "wh")
    await c.answer()

@dp.callback_query(F.data == "msd")
async def ms_done(c: CallbackQuery):
    u, p = c.from_user.id, pair_of(c.from_user.id); put(p[0], "ms", u, {"ok": 1})
    await c.message.edit_text("Missiya bajarildi."); await after(u, p, "ms"); await c.answer()

async def after(u, p, g):
    o = other(p, u)
    if not done(p[0], g, o):
        return await bot.send_message(o, f"Juftingiz «{NAMES[g]}» o'yinini o'ynadi. Siz ham o'ynang.", reply_markup=IM(inline_keyboard=[[IB(text="O'yinlar", callback_data="games")]]))
    d1, d2, pts = get(p[0], g, u), get(p[0], g, o), 0
    if g == "ab":
        for i in range(5):
            pts += 2 * (d1[i][1] == d2[i][0]) + 2 * (d2[i][1] == d1[i][0]) + (d1[i][0] == d2[i][0])
    elif g == "wh":
        pts = 2 * sum(d1[i] == d2[i] for i in range(5))
    else: pts = 10
    db.execute("UPDATE pairs SET pts=pts+? WHERE id=?", (pts, p[0])); db.commit()
    for x in (u, o): await bot.send_message(x, f"«{NAMES[g]}» natijasi: {pts} ball. Ikkalangiz ham qatnashdingiz.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
