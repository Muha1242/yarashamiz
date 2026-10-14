"""Yarashamiz boti v3 (universal): xat + AI yordamchi + o'yinlar + seriya + premium + sovg'a.

Mualliflik: v2 botining kengaytirilgan versiyasi. Barcha eski funksiyalar saqlangan.
Talab qilinadi: Python 3.10+, aiogram>=3.13, SQLite3.
Ishga tushirish: BOT_TOKEN va WEBAPP_URL muhit o'zgaruvchilari berilgach `python bot.py`.
"""
import asyncio, base64, datetime as dt, html, json, os, secrets, sqlite3, time
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fsm_store import SqliteFSM
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
                            WebAppInfo, InlineKeyboardMarkup as IM, InlineKeyboardButton as IB,
                            LabeledPrice, PreCheckoutQuery)

# ============================== SOZLAMALAR ==============================
TOKEN = os.environ.get("BOT_TOKEN", "")


def app_url():
    """Mini App manzili.

    WEBAPP_URL berilmasa Vercel o'z domenidan avtomatik aniqlaydi
    (VERCEL_PROJECT_PRODUCTION_URL -> VERCEL_URL) va /mini_app qo'shadi.
    Bu env unutilsa ham bot ishlashda davom etadi.
    """
    a = (os.environ.get("WEBAPP_URL") or "").strip().rstrip("/")
    if a:
        return a
    # VERCEL_PROJECT_PRODUCTION_URL - doimiy domen (deploy bilan ozgarmaydi),
    # APP_URL - eski sozlama, VERCEL_URL - aniq deploy manzili (oxirgi chora)
    base = (os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
            or os.environ.get("APP_URL")
            or os.environ.get("VERCEL_URL") or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.lower().startswith("http"):
        base = "https://" + base
    return base if base.endswith("/mini_app") else base + "/mini_app"


URL = app_url()
DAILY_LIMIT = 3                                  # bepul: kuniga necha xat
# Telegram Stars narxlari (muhit orqali sozlanadi)
# 1 Star ~ 0.013 USD. Misol: 50 Stars ~ 0.65 USD.
PRICES = {
    "month": int(os.environ.get("PRICE_MONTH", "50")),
    "year": int(os.environ.get("PRICE_YEAR", "400")),
    "gift": int(os.environ.get("PRICE_GIFT", "50")),
}
PREMIUM_DAYS = {"month": 30, "year": 365}

# ============================== KONTENT ================================
OFFERS = ["Birga ovqatlanamiz", "Sayr qilamiz", "Kofe ichamiz", "Kino ko'ramiz", "Sovg'a olaman"]

AB = [("Kofe yoki choy?", "Kofe", "Choy"), ("Tong yoki tun?", "Tong", "Tun"),
      ("Dengiz yoki tog'?", "Dengiz", "Tog'"), ("Kino yoki sayr?", "Kino", "Sayr"),
      ("Shirin yoki sho'r?", "Shirin", "Sho'r"), ("Pitsa yoki kabob?", "Pitsa", "Kabob"),
      ("Yoz yoki qish?", "Yoz", "Qish"), ("It yoki mushuk?", "It", "Mushuk"),
      ("Shahar yoki qishloq?", "Shahar", "Qishloq"), ("Uyda yoki tashqarida?", "Uyda", "Tashqarida")]

WHO = ["Kim ko'proq kech qoladi?", "Kim birinchi kechirim so'raydi?", "Kim ko'proq gapiradi?",
       "Kim ko'proq uxlaydi?", "Kim yaxshi ovqat pishiradi?", "Kim ko'proq telefonda?",
       "Kim ko'proq kuladi?", "Kim ko'proq sevgi bildiradi?"]

QZ = ["Birinchi uchrashuvimiz ajoyib o'tdi.", "Biz haftada bir marta ko'rishardik.",
      "Biz bir-birimizga har kuni sevgi bildiramiz.", "Ba'zida bir-birimizga qo'pol javob beramiz.",
      "Biz birga sayohat qilishni yaxshi ko'ramiz.", "Kelajak rejalarimiz bir xil.",
      "Biz ko'p janjallaymiz.", "Biz bir-birimizni juda yaxshi tushunamiz."]

MISSIONS = ["Bugun juftingizga 3 ta yaxshi gap ayting.",
            "Juftingizning eng yaxshi ko'rgan qo'shig'ini qo'yib bering.",
            "Birga o'tgan eng yaxshi kunni eslab yozing.",
            "Kichik syurpriz qiling: choy yoki shirinlik.",
            "Juftingizdan bugun nima yordam kerakligini so'rang.",
            "Birga rasmga tushing.",
            "Juftingizga ovozli xabar yuboring.",
            "Bugun bir-biringizga nima sevishingizni ayting.",
            "Juftingiz uchun kichik xat yozing.",
            "Birga 10 daqiqa jim o'tirib, qo'lingizni ushlab turing.",
            "Juftingizning ishini yengillashtiring: bir ishni o'zingiz qiling.",
            "Ertangi sanani rejalashtiring va juftingizga ayting."]

THEMES = [("classic", "Klassik"), ("love", "Sevgi ❤️"), ("night", "Tun 🌙"), ("gold", "Oltin ⭐")]
PREMIUM_THEMES = {"night", "gold"}

AI_SIT = {"sorry": "Kechirim so'ramoqchiman", "miss": "Sog'indim", "love": "Sevgi izhori",
          "thank": "Minnatdorchilik", "date": "Uchrashuvga taklif"}
AI_TPL = {
    "sorry": ["Sevgilim, sen menga dunyodagi eng qimmatli insonsan. {w} Kechir meni, men xato "
              "qildim. Yana bir imkoniyat ber, men yaxshiroq bo'laman.",
              "Aziz jonim, bu sukutdan charchadim. {w} Yuragimdagi har bir so'z sen haqida. "
              "Kechir, iltimos, bir bor imkoniyat ber.",
              "Sen bilan bo'lgan har bir daqiqa qadrlim. {w} Meni kechir — boshqacha bo'lmayman, "
              "lekin yaxshilashga va'da beraman."],
    "miss": ["Sog'indim, bunga ishonim komil. {w} Har tong sen bilan uyg'onishni istayman.",
             "Sen yo'q joyda hamma narsa rangsiz. {w} Qachon ko'rishamiz? Yuraksam kelaman.",
             "Ovozimni eshitgim kelyapti. {w} Sog'indim, juda sog'indim."],
    "love": ["Seni sevishimni bugun yana bir bor aytmoqchiman. {w} Sen mening tanlangan insonim.",
             "Yurak urishi — bu sen. {w} Seni sevaman, bugun ham, ertaga ham.",
             "Dunyoda eng go'zal his — bu sen bilan bo'lish. {w} Sevaman."],
    "thank": ["Rahmat, chunki sen borasan. {w} Seni qadrlayman.",
              "Bugun seni minnatdorlik bilan eslayapman. {w} Rahmat, jonim.",
              "Sen uchun aytadigan eng muhim so'z: rahmat. {w} Qadrim."],
    "date": ["Birga vaqt o'tkazaylik. {w} Taklifim shu: bugun kechqurun birga bo'lamiz.",
             "Syurpriz qilmoqchiman: seni taklif etaman. {w} Roziligini bilmoqchiman.",
             "Uchrashamizmi? {w} Men seni kutaman, roziligingizni aytishingiz kifoya."],
}
FALLBACK = "Sen bilan birga bo'lgan har bir lahza men uchun qimmat."

TIPS = ["Hissiyotlaringizni 'sen' deb emas, 'men' deb boshlang: 'men xafa bo'ldim'.",
        "Araz 24 soatdan oshmasin — vaqt his-tuyg'ularni kuchaytiradi.",
        "Kechirim so'rashda ayblash emas, o'z hissingizni ayting.",
        "Kichik syurprizlar katta yuraklarni ochadi.",
        "Bir-biringizning sevgi tilini bilib oling: sovg'a, vaqt, so'z, yordam, tegish."]

WELCOME = ("Salom! Men <b>Yarashamiz</b> botiman ❤️\n\n"
           "Arazni chiroyli xat bilan tugatamiz, so'ngra birga o'ynaymiz "
           "va seriyani buzmaymiz 🔥\n\n"
           "Nima qilmoqchisiz?")

HELP = ("<b>Qanday ishlaydi?</b>\n\n"
        "1. «✍️ Xat yozish» — uzr yoki sevgi xatingizni yozing.\n"
        "2. Uchrashuv taklifini tanlang va havolani juftingizga yuboring.\n"
        "3. U xatni ochadi va javob beradi.\n"
        "4. Yarashgach, «🎮 O'yinlar» bo'limida birga o'ynab ball to'playsiz.\n\n"
        "<b>Ball va seriya</b>\n"
        "• Ball: o'yinlarda mos javoblar 🎯\n"
        "• 🔥 Seriya: har kun o'yin o'ynasangiz uzaydi.\n\n"
        "/menu — bosh menyu\n/cancel — bekor qilish\n/help — yordam")

# ============================ MA'LUMOTLAR BAZASI =======================
# Vercel uchun: sqlite ulanishini almashtirish mumkin bolgan qobiq.
# Fayl yo'li DB_PATH orqali beriladi (Vercel'da /tmp/bot.db).
class _DB:
    """sqlite ulanishining qobig'i. Har so'rovda bazani qayta ochish imkonini beradi."""

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=15)

    def reopen(self):
        """Ulanishni yopib, qaytadan ochadi (Redis'dan yangi baza olgach)."""
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=15)
        return self.conn

    def __getattr__(self, name):
        return getattr(self.conn, name)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS letters(id INTEGER PRIMARY KEY, sender INT, receiver INT, text TEXT,
                                   offers TEXT, theme TEXT DEFAULT 'classic', ts INT);
CREATE TABLE IF NOT EXISTS blocked(user INT, sender INT, PRIMARY KEY(user, sender));
CREATE TABLE IF NOT EXISTS pairs(id INTEGER PRIMARY KEY, a INT, b INT, pts INT DEFAULT 0,
                                 ts INT DEFAULT 0, UNIQUE(a,b));
CREATE TABLE IF NOT EXISTS ans(pair INT, day TEXT, game TEXT, user INT, data TEXT,
                               PRIMARY KEY(pair,day,game,user));
CREATE TABLE IF NOT EXISTS streaks(user INT PRIMARY KEY, last TEXT, n INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS premium(user INT PRIMARY KEY, until INT);
CREATE TABLE IF NOT EXISTS gifts(token TEXT PRIMARY KEY, days INT, used INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS sent(user INT, kind TEXT, day TEXT, PRIMARY KEY(user,kind,day));
"""


def init_db(conn):
    """Jadval va ustunlarni yaratadi. Qayta chaqirish xavfsiz (migratsiya)."""
    conn.executescript(_SCHEMA)
    for _col, _ddl in [("theme", "TEXT DEFAULT 'classic'"), ("receiver", "INT"),
                       ("ts", "INT DEFAULT 0")]:
        _tbl = "pairs" if _col == "ts" else "letters"
        try:
            conn.execute(f"ALTER TABLE {_tbl} ADD COLUMN {_col} {_ddl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


db = _DB(os.environ.get("DB_PATH", "bot.db"))
init_db(db.conn)

today = lambda: dt.date.today().isoformat()

GAMES = {
    "ab": {"name": "A yoki B", "n": 5, "mode": "guess", "qs": AB},
    "wh": {"name": "Kim ko'proq?", "n": 5, "mode": "match", "opt": ("Men", "U"), "qs": WHO},
    "ms": {"name": "Kunlik missiya", "n": 1, "mode": "mission", "qs": MISSIONS},
    "qz": {"name": "Sevgi kvizi", "n": 6, "mode": "match", "opt": ("Ha", "Yo'q"), "qs": QZ,
           "prem": True},
}


def pair_of(u):
    return db.execute("SELECT id,a,b FROM pairs WHERE a=? OR b=? ORDER BY id DESC LIMIT 1",
                      (u, u)).fetchone()


def other(p, u):
    return p[2] if p[1] == u else p[1]


def get(pid, g, u):
    r = db.execute("SELECT data FROM ans WHERE pair=? AND day=? AND game=? AND user=?",
                   (pid, today(), g, u)).fetchone()
    return json.loads(r[0]) if r else None


def put(pid, g, u, d):
    db.execute("INSERT OR REPLACE INTO ans VALUES(?,?,?,?,?)",
               (pid, today(), g, u, json.dumps(d)))
    db.commit()


def done(pid, g, u):
    d, gg = get(pid, g, u), GAMES[g]
    if d is None:
        return False
    return len(d) >= gg["n"] if gg["mode"] != "mission" else bool(d.get("ok"))


def qidx(g, step):
    """Kunlik aylanish: ikkala juftlik a'zosi bir xil savolni ko'radi."""
    return (dt.date.today().toordinal() + step) % len(GAMES[g]["qs"])


def touch(u):
    """Kunlik seriyani yangilaydi, yangi qiymatni qaytaradi."""
    t = today()
    r = db.execute("SELECT last,n FROM streaks WHERE user=?", (u,)).fetchone()
    if not r:
        n = 1
        db.execute("INSERT INTO streaks VALUES(?,?,1)", (u, t))
    elif r[0] == t:
        n = r[1]
    else:
        n = r[1] + 1 if r[0] == (dt.date.today() - dt.timedelta(1)).isoformat() else 1
        db.execute("UPDATE streaks SET last=?,n=? WHERE user=?", (t, n, u))
    db.commit()
    return n


def streak(u):
    r = db.execute("SELECT last,n FROM streaks WHERE user=?", (u,)).fetchone()
    return r[1] if r else 0


def is_prem(u):
    r = db.execute("SELECT until FROM premium WHERE user=?", (u,)).fetchone()
    return bool(r and r[0] >= int(dt.datetime.now().timestamp()))


def prem_days(u):
    r = db.execute("SELECT until FROM premium WHERE user=?", (u,)).fetchone()
    return 0 if not r else max(0, round((r[0] - int(dt.datetime.now().timestamp())) / 86400))


def add_prem(u, days):
    base = dt.datetime.now().timestamp()
    if is_prem(u):
        base = db.execute("SELECT until FROM premium WHERE user=?", (u,)).fetchone()[0]
    db.execute("INSERT OR REPLACE INTO premium VALUES(?,?)", (u, int(base + days * 86400)))
    db.commit()


def sent(u, kind):
    return db.execute("SELECT 1 FROM sent WHERE user=? AND kind=? AND day=?",
                      (u, kind, today())).fetchone() is not None


def mark(u, kind):
    db.execute("INSERT OR IGNORE INTO sent VALUES(?,?,?)", (u, kind, today()))
    db.commit()


def make_gift(days):
    token = secrets.token_urlsafe(8)
    db.execute("INSERT INTO gifts VALUES(?,?,0)", (token, days))
    db.commit()
    return token


def use_gift(token, u):
    r = db.execute("SELECT days,used FROM gifts WHERE token=?", (token,)).fetchone()
    if not r or r[1]:
        return 0
    db.execute("UPDATE gifts SET used=1 WHERE token=?", (token,))
    db.commit()
    add_prem(u, r[0])
    return r[0]


def theme_ok(theme, u):
    return theme not in PREMIUM_THEMES or is_prem(u)


# ============================== KO'RINISHLAR ===========================
def main_kb():
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="✍️ Xat yozish"), KeyboardButton(text="🎮 O'yinlar")],
        [KeyboardButton(text="📊 Hisobim"), KeyboardButton(text="💌 Xotiralar")],
        [KeyboardButton(text="🏆 Yutuqlar"), KeyboardButton(text="💎 Premium")],
    ])


def menu_kb(u):
    rows = [[IB(text="✍️ Xat yozish", callback_data="new")]]
    if pair_of(u):
        rows.append([IB(text="🎮 O'yinlar", callback_data="games")])
    rows += [[IB(text="📊 Hisobim", callback_data="stats"),
              IB(text="💌 Xotiralar", callback_data="lib")],
             [IB(text="🏆 Yutuqlar", callback_data="badges")],
             [IB(text="💎 Premium", callback_data="prem")]]
    return IM(inline_keyboard=rows)


def offer_kb(sel):
    rows = [[IB(text=("✅ " if o in sel else "") + o, callback_data=f"o:{i}")]
            for i, o in enumerate(OFFERS)]
    return IM(inline_keyboard=rows + [[IB(text="Tayyor", callback_data="done")]])


def theme_kb(u):
    return IM(inline_keyboard=[[IB(text=name + (" 🔒" if not theme_ok(t, u) else ""),
                                   callback_data=f"th:{t}")] for t, name in THEMES])


def open_letter_kb(lid, link):
    btn = KeyboardButton(text="💌 Xatni ochish",
                         web_app=WebAppInfo(url=f"{URL}/?d={link}&l={lid}"))
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[btn]])


def games_view(u):
    p = pair_of(u)
    if not p:
        return None, None
    o, rows = other(p, u), []
    txt = "Bugungi o'yinlar. Ball faqat ikkalangiz ham o'ynasangiz beriladi.\n\n"
    for g, gg in GAMES.items():
        me, him = done(p[0], g, u), done(p[0], g, o)
        name = gg["name"] + (" 💎" if gg.get("prem") else "")
        txt += f"{name}: siz {'✅' if me else '⏳'}, juftingiz {'✅' if him else '⏳'}\n"
        if not me:
            lock = bool(gg.get("prem")) and not is_prem(u)
            rows.append([IB(text=("🔒 " if lock else "") + gg["name"], callback_data=f"go:{g}")])
    pts = db.execute("SELECT pts FROM pairs WHERE id=?", (p[0],)).fetchone()[0]
    return txt + f"\nJuftlik bali: {pts}", IM(
        inline_keyboard=rows or [[IB(text="Premium 💎", callback_data="prem")]])


def profile_view(u):
    p = pair_of(u)
    pts, days = 0, "—"
    if p:
        pts, ts = db.execute("SELECT pts,ts FROM pairs WHERE id=?", (p[0],)).fetchone()
        if ts:
            days = (dt.date.today() - dt.date.fromtimestamp(ts)).days
    st, prem = streak(u), is_prem(u)
    tip = TIPS[dt.date.today().toordinal() % len(TIPS)]
    return (f"📊 <b>Hisobingiz</b>\n\n"
            f"🔥 Ketma-kunlik seriya: <b>{st}</b> kun\n"
            f"⭐ Juftlik bali: <b>{pts}</b>\n"
            f"❤️ Birga kunlar: <b>{days}</b>\n"
            f"💎 Premium: <b>{'faol' if prem else 'yo‘q'}</b>"
            + (f" ({prem_days(u)} kun qoldi)" if prem else "") + "\n\n"
            f"💡 <i>{tip}</i>")


def badges_view(u):
    p = pair_of(u)
    pts = db.execute("SELECT pts FROM pairs WHERE id=?", (p[0],)).fetchone()[0] if p else 0
    n_letters = db.execute("SELECT COUNT(*) FROM letters WHERE sender=?", (u,)).fetchone()[0]
    st = streak(u)
    items = [("✉️ Birinchi xat", n_letters >= 1), ("❤️ Yarashtiruvchi", bool(p)),
             ("🔥 3 kunlik seriya", st >= 3), ("🔥 7 kunlik seriya", st >= 7),
             ("🔥 30 kunlik seriya", st >= 30), ("⭐ 100 ball", pts >= 100),
             ("⭐ 500 ball", pts >= 500), ("💎 Premium a'zosi", is_prem(u))]
    txt = "🏆 <b>Yutuqlar</b>\n\n" + "\n".join(
        f"{'✅' if ok else '⬜'} {name}" for name, ok in items)
    return txt, IM(inline_keyboard=[[IB(text="🎮 O'yinlar", callback_data="games")]])


def library_view(u):
    rows = db.execute(
        "SELECT id,text,ts,sender FROM letters WHERE sender=? OR receiver=? "
        "ORDER BY ts DESC LIMIT 20", (u, u)).fetchall()
    if not rows:
        return "💌 Xotiralar bo'sh. Birinchi xatingizni yozing!"
    out = ["💌 <b>Xotiralar</b>\n"]
    for i, (lid, text, ts, sender) in enumerate(rows):
        d = dt.datetime.fromtimestamp(ts).strftime("%d.%m")
        out.append(f"{i+1}. {d} {'siz →' if sender == u else '→ siz'} «{html.escape(text[:40])}…»")
    return "\n".join(out) + "\n\n<b>Premium</b> bilan xotiralar cheksiz saqlanadi 💎"


def premium_view(u):
    if is_prem(u):
        return (f"💎 <b>Premium faol</b> — {prem_days(u)} kun qoldi.\n\n"
                "Cheksiz xat, AI yordamchi, barcha shablonlar va o'yinlar sizniki.")
    return ("💎 <b>Premium</b> nima beradi?\n"
            "• ✍️ Cheksiz xat (bepulda kuniga 3)\n"
            "• ✨ AI yordamchi: uzr, sevgi, uchrashuv xatlarini yozib beradi\n"
            "• 🎨 Maxsus xat shablonlari (Tun, Oltin)\n"
            "• 🎮 Qo'shimcha o'yin: Sevgi kvizi\n"
            "• 💌 Xotiralar cheksiz saqlanadi\n"
            "• 🥇 Maxsus yutuqlar va nishonlar\n\n"
            f"Narx: <b>{PRICES['month']} ⭐</b> (oy) yoki "
            f"<b>{PRICES['year']} ⭐</b> (yil, 2 oy bepul).")


def prem_kb():
    return IM(inline_keyboard=[
        [IB(text=f"⭐ {PRICES['month']} — 1 oy", callback_data="buy:month"),
         IB(text=f"⭐ {PRICES['year']} — 1 yil", callback_data="buy:year")],
        [IB(text=f"🎁 {PRICES['gift']} ⭐ — sovg'a qilish", callback_data="buy:gift")]])


def mission_of_day():
    return MISSIONS[dt.date.today().toordinal() % len(MISSIONS)]


# ============================== FSM HOLATLAR ===========================
class W(StatesGroup):
    text = State()
    offers = State()
    theme = State()
    ai_sit = State()
    ai_words = State()


# ============================== XAT OQIMI ==============================
bot, dp = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)), Dispatcher(storage=SqliteFSM(db))
def variants(sit, words):
    """Shablonlardan 3 xil xat varianti yasaydi."""
    words = (words or "").strip() or FALLBACK
    return [t.replace("{w}", words) for t in AI_TPL[sit]]


async def do_new(m: Message, state: FSMContext):
    u = m.from_user.id
    n = db.execute("SELECT COUNT(*) FROM letters WHERE sender=? AND ts>?",
                   (u, time.time() - 86400)).fetchone()[0]
    if n >= DAILY_LIMIT and not is_prem(u):
        return await m.answer(
            "Bugungi bepul limit (3 xat) tugadi. Ertaga yozing yoki 💎 Premium oling — "
            "cheksiz xat yoziladi.")
    await state.set_state(W.text)
    await m.answer("Xat matnini yozing (300 belgigacha). Uzr so'rang, samimiy bo'ling.",
                   reply_markup=IM(inline_keyboard=[
                       [IB(text="✨ AI yordamchi bilan yozish", callback_data="ai")]]))


@dp.message(F.web_app_data)
async def reply(m: Message, bot: Bot):
    r = json.loads(m.web_app_data.data)
    u = m.from_user.id
    row = db.execute("SELECT sender FROM letters WHERE id=?", (r.get("l"),)).fetchone()
    sender = row[0] if row else None
    if not sender:
        return await m.answer("Xat topilmadi.")
    if sender == u:
        return await m.answer("Bu o'z xatingiz 🙂")
    if r["a"] == "stop":
        db.execute("INSERT OR IGNORE INTO blocked VALUES(?,?)", (u, sender))
        db.commit()
        return await m.answer("Tushunarli. Bu yuboruvchidan boshqa xat kelmaydi.")
    if r["a"] == "heart":
        touch(u)
        await bot.send_message(sender, "💝 Sizga yurak yuborildi! Javobingizni kutmoqda.")
        return await m.answer("💝 Yurak yuborildi.")
    if r["a"] == "yes":
        ex = db.execute("SELECT id FROM pairs WHERE (a=? AND b=?) OR (b=? AND a=?)",
                        (sender, u, sender, u)).fetchone()
        if not ex:
            db.execute("INSERT INTO pairs(a,b,ts) VALUES(?,?,?)",
                       (sender, u, int(time.time())))
            db.commit()
        db.execute("UPDATE letters SET receiver=? WHERE id=?", (u, r.get("l")))
        db.commit()
        touch(u)
        touch(sender)
        await bot.send_message(sender, "Javob: <b>yarashamiz</b> 🎉 "
                               f"Taklif: {r.get('o')}\nEndi birga o'ynashingiz mumkin.",
                               reply_markup=menu_kb(sender))
        return await m.answer("Yarashdingiz 🎉 Endi birga o'ynang.",
                              reply_markup=menu_kb(u))
    if r["a"] == "later":
        await bot.send_message(sender, "Javob: hali tayyor emas, keyinroq ⏳")
    await m.answer("Javobingiz yuborildi.")


# ============================== HANDLERLAR =============================
@dp.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext, bot: Bot):
    await state.clear()
    arg = command.args or ""
    if arg.startswith("l_"):
        lid = arg[2:]
        row = db.execute("SELECT sender,text,offers,theme FROM letters WHERE id=?",
                         (lid,)).fetchone()
        if not row:
            return await m.answer("Xat topilmadi.")
        sender, text, offers, theme = row
        if db.execute("SELECT 1 FROM blocked WHERE user=? AND sender=?",
                      (m.from_user.id, sender)).fetchone():
            return await m.answer("Bu yuboruvchidan xat olmaslikni tanlagansiz.")
        payload = base64.urlsafe_b64encode(json.dumps(
            {"t": text, "o": json.loads(offers), "theme": theme}).encode()).decode()
        return await m.answer("Sizga xat bor 💌", reply_markup=open_letter_kb(lid, payload))
    if arg.startswith("gift_"):
        days = use_gift(arg[5:], m.from_user.id)
        if days:
            touch(m.from_user.id)
            return await m.answer(f"🎁 Sovg'a qabul qilindi! Sizga <b>{days} kun</b> "
                                  "premium berildi 💎", reply_markup=menu_kb(m.from_user.id))
        return await m.answer("Bu sovg'a allaqachon ishlatilgan yoki yaroqsiz.")
    touch(m.from_user.id)
    await m.answer(WELCOME, reply_markup=main_kb())
    await m.answer("Asosiy menyu:", reply_markup=menu_kb(m.from_user.id))


@dp.message(Command("menu"))
async def menu_cmd(m: Message):
    await m.answer("Asosiy menyu:", reply_markup=menu_kb(m.from_user.id))


@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP)


@dp.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.", reply_markup=menu_kb(m.from_user.id))


@dp.callback_query(F.data == "new")
async def new(c: CallbackQuery, state: FSMContext):
    await do_new(c.message, state)
    await c.answer()


@dp.message(W.text, F.text)
async def got_text(m: Message, state: FSMContext):
    await state.update_data(text=m.text[:300], offers=[])
    await state.set_state(W.offers)
    await m.answer("Qanday uchrashuv taklif qilasiz? (bir nechtasini tanlang)",
                   reply_markup=offer_kb([]))


@dp.callback_query(W.offers, F.data.startswith("o:"))
async def toggle(c: CallbackQuery, state: FSMContext):
    o = OFFERS[int(c.data[2:])]
    sel = (await state.get_data())["offers"]
    sel = [x for x in sel if x != o] if o in sel else sel + [o]
    await state.update_data(offers=sel)
    await c.message.edit_reply_markup(reply_markup=offer_kb(sel))
    await c.answer()


@dp.callback_query(W.offers, F.data == "done")
async def finish(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if not d["offers"]:
        return await c.answer("Kamida bitta taklif tanlang", show_alert=True)
    await state.set_state(W.theme)
    await c.message.answer("Xat qanday ko'rinishda bo'lsin?",
                           reply_markup=theme_kb(c.from_user.id))
    await c.answer()


@dp.callback_query(W.theme, F.data.startswith("th:"))
async def theme(c: CallbackQuery, state: FSMContext, bot: Bot):
    t = c.data[3:]
    if not theme_ok(t, c.from_user.id):
        return await c.answer("Bu shablon premium uchun 💎", show_alert=True)
    d = await state.get_data()
    cur = db.execute("INSERT INTO letters(sender,text,offers,theme,ts) VALUES(?,?,?,?,?)",
                     (c.from_user.id, d["text"], json.dumps(d["offers"]), t, int(time.time())))
    db.commit()
    await state.clear()
    me = await bot.get_me()
    touch(c.from_user.id)
    await c.message.answer("Xat tayyor. Havolani juftingizga o'zingiz yuboring:\n"
                           f"https://t.me/{me.username}?start=l_{cur.lastrowid}")
    await c.answer()


# ------------------------------- AI ------------------------------------
@dp.callback_query(F.data == "ai")
async def ai_start(c: CallbackQuery, state: FSMContext):
    if not is_prem(c.from_user.id):
        return await c.answer("✨ AI yordamchi — premium funksiya 💎", show_alert=True)
    await state.set_state(W.ai_sit)
    await c.message.answer("Nima yozmoqchisiz?",
                           reply_markup=IM(inline_keyboard=[
                               [IB(text=v, callback_data=f"as:{k}")]
                               for k, v in AI_SIT.items()]))
    await c.answer()


@dp.callback_query(W.ai_sit, F.data.startswith("as:"))
async def ai_sit(c: CallbackQuery, state: FSMContext):
    await state.update_data(sit=c.data[3:])
    await state.set_state(W.ai_words)
    await c.message.answer("Kalit so'zlarni yozing (masalan: «tug'ilgan kun», "
                           "«kechirasiz», «birga kino»). Yozmasangiz — o'zim yozaman.")
    await c.answer()


@dp.message(W.ai_words, F.text)
async def ai_words(m: Message, state: FSMContext):
    d = await state.get_data()
    vs = variants(d["sit"], m.text)
    await state.update_data(words=m.text, variants=vs, vi=0)
    await state.set_state(W.text)
    await m.answer("✨ Mana shunday xat:\n\n" + html.escape(vs[0]),
                   reply_markup=IM(inline_keyboard=[
                       [IB(text="♻️ Boshqa variant", callback_data="aiv:1"),
                        IB(text="✅ Ishlatish", callback_data="aiu")]]))


@dp.callback_query(F.data.startswith("aiv:"))
async def ai_variant(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    vs = d.get("variants") or []
    if not vs:
        return await c.answer("Avval kalit so'zlarni yozing", show_alert=True)
    i = int(c.data[4:]) % len(vs)
    await state.update_data(vi=i)
    await c.message.edit_text("✨ Variant:\n\n" + html.escape(vs[i]),
                              reply_markup=IM(inline_keyboard=[
                                  [IB(text="♻️ Boshqa variant",
                                      callback_data=f"aiv:{(i + 1) % len(vs)}"),
                                   IB(text="✅ Ishlatish", callback_data="aiu")]]))
    await c.answer()


@dp.callback_query(F.data == "aiu")
async def ai_use(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    vs, i = d.get("variants") or [""], d.get("vi", 0)
    await state.update_data(text=vs[i][:300], offers=[])
    await state.set_state(W.offers)
    await c.message.answer("Zo'r! Endi uchrashuv taklifini tanlang:",
                           reply_markup=offer_kb([]))
    await c.answer()


# ------------------------------ MENYU ----------------------------------
@dp.callback_query(F.data == "games")
async def games_cb(c: CallbackQuery):
    t, kb = games_view(c.from_user.id)
    if not t:
        return await c.answer("Avval xat orqali yarashing ❤️", show_alert=True)
    await c.message.answer(t, reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data == "stats")
async def stats_cb(c: CallbackQuery):
    touch(c.from_user.id)
    await c.message.answer(profile_view(c.from_user.id))
    await c.answer()


@dp.callback_query(F.data == "badges")
async def badges_cb(c: CallbackQuery):
    t, kb = badges_view(c.from_user.id)
    await c.message.answer(t, reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data == "lib")
async def lib_cb(c: CallbackQuery):
    await c.message.answer(library_view(c.from_user.id))
    await c.answer()


@dp.callback_query(F.data == "prem")
async def prem_cb(c: CallbackQuery):
    await c.message.answer(premium_view(c.from_user.id),
                           reply_markup=None if is_prem(c.from_user.id) else prem_kb())
    await c.answer()


@dp.callback_query(F.data == "menu")
async def menu_cb(c: CallbackQuery):
    await c.message.answer("Asosiy menyu:", reply_markup=menu_kb(c.from_user.id))
    await c.answer()


# ----------------------------- TO'LOVLAR -------------------------------
@dp.callback_query(F.data.startswith("buy:"))
async def buy(c: CallbackQuery, bot: Bot):
    kind = c.data[4:]
    payload = ("gift" if kind == "gift" else f"prem:{kind}") + f":{c.from_user.id}"
    await bot.send_invoice(
        chat_id=c.from_user.id, title="Yarashamiz Premium 💎",
        description={"month": "1 oylik premium: cheksiz xat, AI yordamchi, barcha shablonlar.",
                     "year": "1 yillik premium (2 oy bepul).",
                     "gift": "Juftingizga 30 kunlik premium sovg'a."}[kind],
        payload=payload, provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=PRICES[kind])])
    await c.answer()


@dp.pre_checkout_query()
async def pre(q: PreCheckoutQuery):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def paid(m: Message, bot: Bot):
    parts = m.successful_payment.invoice_payload.split(":")
    if parts[0] == "prem":
        kind = parts[1]
        add_prem(int(parts[2]), PREMIUM_DAYS[kind])
        await m.answer(f"💎 Premium faollashdi! {PREMIUM_DAYS[kind]} kunlik imtiyozlar "
                       "sizniki.\n«✍️ Xat yozish» ichida ✨ AI yordamchini sinab ko'ring.")
    else:
        token = make_gift(30)
        me = await bot.get_me()
        await m.answer("🎁 Sovg'a tayyor! Bu havolani juftingizga yuboring — u 30 kun "
                       f"premium oladi:\nhttps://t.me/{me.username}?start=gift_{token}")


# --------------------------- PASTKI TUGMALAR ---------------------------
@dp.message(F.text == "✍️ Xat yozish", StateFilter(None))
async def btn_new(m: Message, state: FSMContext):
    await do_new(m, state)


@dp.message(F.text == "🎮 O'yinlar")
async def btn_games(m: Message):
    t, kb = games_view(m.from_user.id)
    await m.answer(t or "Avval xat orqali yarashing ❤️", reply_markup=kb)


@dp.message(F.text == "📊 Hisobim")
async def btn_stats(m: Message):
    touch(m.from_user.id)
    await m.answer(profile_view(m.from_user.id))


@dp.message(F.text == "💌 Xotiralar")
async def btn_lib(m: Message):
    await m.answer(library_view(m.from_user.id))


@dp.message(F.text == "🏆 Yutuqlar")
async def btn_badges(m: Message):
    t, kb = badges_view(m.from_user.id)
    await m.answer(t, reply_markup=kb)


@dp.message(F.text == "💎 Premium")
async def btn_prem(m: Message):
    await m.answer(premium_view(m.from_user.id),
                   reply_markup=None if is_prem(m.from_user.id) else prem_kb())


# ============================== O'YINLAR ===============================
def ab_kb(i):
    q, a, b = AB[i]
    return q, IM(inline_keyboard=[[IB(text=a, callback_data=f"abo:{i}:0"),
                                    IB(text=b, callback_data=f"abo:{i}:1")]])


async def ask_match(msg, g, step):
    gg = GAMES[g]
    q, a, b = gg["qs"][qidx(g, step)], *gg["opt"]
    await msg.answer(f"{step + 1}/{gg['n']}. {q}",
                     reply_markup=IM(inline_keyboard=[
                         [IB(text=a, callback_data=f"mg:{g}:{step}:0"),
                          IB(text=b, callback_data=f"mg:{g}:{step}:1")]]))


async def after(u, p, g, bot: Bot):
    """Ikkalasi ham o'ynagach ball hisoblanadi."""
    o = other(p, u)
    if not done(p[0], g, o):
        return await bot.send_message(
            o, f"Juftingiz «{GAMES[g]['name']}» o'yinini o'ynadi. Siz ham o'ynang.",
            reply_markup=IM(inline_keyboard=[[IB(text="🎮 O'yinlar", callback_data="games")]]))
    d1, d2, gg = get(p[0], g, u), get(p[0], g, o), GAMES[g]
    if gg["mode"] == "match":
        pts = 2 * sum(d1[i] == d2[i] for i in range(gg["n"]))
        if d1 == d2:
            pts += 5
    elif g == "ab":
        pts = sum(2 * (d1[i][1] == d2[i][0]) + 2 * (d2[i][1] == d1[i][0])
                  + (d1[i][0] == d2[i][0]) for i in range(5))
    else:
        pts = 10
    db.execute("UPDATE pairs SET pts=pts+? WHERE id=?", (pts, p[0]))
    db.commit()
    touch(u)
    for x in (u, o):
        await bot.send_message(x, f"«{gg['name']}» natijasi: {pts} ball 🎯 "
                                  "Ikkalangiz ham qatnashdingiz.")


@dp.callback_query(F.data.startswith("go:"))
async def go(c: CallbackQuery):
    g = c.data[3:]
    u, p = c.from_user.id, pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval xat orqali yarashing ❤️", show_alert=True)
    gg = GAMES[g]
    if gg.get("prem") and not is_prem(u):
        return await c.answer("Bu o'yin premium uchun 💎", show_alert=True)
    if done(p[0], g, u):
        return await c.answer("Bugun o'ynagansiz ✅")
    if gg["mode"] == "mission":
        await c.message.answer("Bugungi missiya:\n" + mission_of_day(),
                               reply_markup=IM(inline_keyboard=[
                                   [IB(text="✅ Bajardim", callback_data="msd")]]))
    elif gg["mode"] == "guess":
        q, kb = ab_kb(qidx(g, 0))
        await c.message.answer("Avval o'zingiz tanlang, keyin juftingiz nimani "
                               "tanlashini toping.\n\n" + q, reply_markup=kb)
    else:
        await ask_match(c.message, g, 0)
    await c.answer()


@dp.callback_query(F.data.startswith("abo:"))
async def ab_own(c: CallbackQuery):
    _, i, o = c.data.split(":")
    u, p = c.from_user.id, pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    d = get(p[0], "ab", u) or []
    if int(i) != qidx("ab", len(d)):
        return await c.answer()
    q, a, b = AB[int(i)]
    await c.message.edit_text(f"{q}\nSiz: {(a, b)[int(o)]}. Juftingiz nimani tanlaydi?",
                              reply_markup=IM(inline_keyboard=[
                                  [IB(text=a, callback_data=f"abg:{i}:{o}:0"),
                                   IB(text=b, callback_data=f"abg:{i}:{o}:1")]]))
    await c.answer()


@dp.callback_query(F.data.startswith("abg:"))
async def ab_guess(c: CallbackQuery, bot: Bot):
    _, i, o, g = c.data.split(":")
    u, p = c.from_user.id, pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    d = get(p[0], "ab", u) or []
    if int(i) != qidx("ab", len(d)):
        return await c.answer()
    d.append([int(o), int(g)])
    put(p[0], "ab", u, d)
    if len(d) < GAMES["ab"]["n"]:
        q, kb = ab_kb(qidx("ab", len(d)))
        await c.message.edit_text(q, reply_markup=kb)
    else:
        await c.message.edit_text("Tayyor ✅")
        await after(u, p, "ab", bot)
    await c.answer()


@dp.callback_query(F.data.startswith("mg:"))
async def mg(c: CallbackQuery, bot: Bot):
    _, g, step, x = c.data.split(":")
    u, p = c.from_user.id, pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    gg = GAMES[g]
    if gg.get("prem") and not is_prem(u):
        return await c.answer("Bu o'yin premium uchun 💎", show_alert=True)
    d = get(p[0], g, u) or []
    if len(d) != int(step):
        return await c.answer()
    d.append(int(x))
    put(p[0], g, u, d)
    if len(d) < gg["n"]:
        q, a, b = gg["qs"][qidx(g, len(d))], *gg["opt"]
        await c.message.edit_text(f"{len(d) + 1}/{gg['n']}. {q}",
                                  reply_markup=IM(inline_keyboard=[
                                      [IB(text=a, callback_data=f"mg:{g}:{len(d)}:0"),
                                       IB(text=b, callback_data=f"mg:{g}:{len(d)}:1")]]))
    else:
        await c.message.edit_text("Tayyor ✅")
        await after(u, p, g, bot)
    await c.answer()


@dp.callback_query(F.data == "msd")
async def ms_done(c: CallbackQuery, bot: Bot):
    u, p = c.from_user.id, pair_of(c.from_user.id)
    put(p[0], "ms", u, {"ok": 1})
    await c.message.edit_text("Missiya bajarildi ✅")
    await after(u, p, "ms", bot)
    await c.answer()


# ============================== ESLATMALAR =============================
# Vercel serveri UTC vaqtida ishlaydi, eslatma esa mahalliy vaqtda kerak.
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "5"))   # O'zbekiston = UTC+5


def local_hour():
    """Mahalliy soat (UTC + TZ_OFFSET)."""
    return (dt.datetime.utcnow().hour + TZ_OFFSET) % 24


async def reminders_once():
    """Bir marta ishlaydi: missiya va seriya eslatmalarini yuboradi.

    Vercel Cron tomonidan chaqiriladi (api/cron.py), shuning uchun
    cheksiz sikl YO'Q.
    """
    h = local_hour()
    for (u,) in db.execute("SELECT user FROM streaks").fetchall():
        p = pair_of(u)
        if not p:
            continue
        if h >= 19 and not sent(u, "ms") and not done(p[0], "ms", u):
            try:
                await bot.send_message(u, "🌙 Bugungi missiya bajarilmagan. "
                                       "Juftingizni bir gaplashib, birga qiling!")
            except Exception:
                pass
            mark(u, "ms")
        r = db.execute("SELECT last,n FROM streaks WHERE user=?", (u,)).fetchone()
        if r and r[1] >= 3 and r[0] != today() and not sent(u, "st"):
            try:
                await bot.send_message(u, f"🔥 Seriyani buzma! {r[1]} kunlik "
                                       "seriyangiz bor. Bugun bir o'yin o'ynang.")
            except Exception:
                pass
            mark(u, "st")


async def reminders():
    """Doimiy sikl - faqat polling (lokal) rejimida ishlatiladi."""
    while True:
        try:
            await reminders_once()
        except Exception:
            pass
        await asyncio.sleep(3600)


# ============================== ISHGA TUSHIRISH ========================
async def main():
    asyncio.create_task(reminders())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
