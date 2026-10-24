"""Yarashamiz boti v3.1 — VERCEL/WEBHOOK + haqiqiy AI + kunlik savol.

v3.1 qo'shimchalari:
- ✨ Haqiqiy AI xat yozish (Google Gemini; kalit bo'lmasa shablon bilan davom etadi)
- 💬 Kunlik savol o'yini (har kuni bitta savol, ikkalasi ham javob beradi, +5 ball)
- 📊 /admin hisobot (faqat ADMIN_ID uchun)

Muhit o'zgaruvchilari:
  BOT_TOKEN, WEBAPP_URL, REDIS_URL  — v3 dagidek
  GEMINI_API_KEY — (ixtiyoriy) https://aistudio.google.com/apikey
  ADMIN_ID       — (ixtiyoriy) sizning Telegram ID'ingiz
"""
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis as ARedis
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import ai_helper

# ---------------------------- SOZLAMALAR --------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "")


def app_url():
    """Mini App manzili. WEBAPP_URL bo'lmasa Vercel domenidan aniqlanadi."""
    a = (os.environ.get("WEBAPP_URL") or "").strip().rstrip("/")
    if a:
        return a
    base = (os.environ.get("VERCEL_PROJECT_PRODUCTION_URL")
            or os.environ.get("APP_URL")
            or os.environ.get("VERCEL_URL") or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.lower().startswith("http"):
        base = "https://" + base
    return base if base.endswith("/mini_app") else base + "/mini_app"


URL = app_url()
ADMIN_ID = os.environ.get("ADMIN_ID", "")
DAILY_LIMIT = 3
# Telegram Stars narxlari (muhit orqali sozlanadi)
PRICES = {
    "month": int(os.environ.get("PRICE_MONTH", "50")),
    "year": int(os.environ.get("PRICE_YEAR", "500")),
    "gift": int(os.environ.get("PRICE_GIFT", "80")),
}
# "1 yil + 2 oy" = 425 kun (matndagi va'da bilan mos)
PREMIUM_DAYS = {"month": 30, "year": 425}
GIFT_DAYS = int(os.environ.get("GIFT_DAYS", "30"))

# ------------------------------ KONTENT ---------------------------------
OFFERS = ["Birga ovqatlanamiz", "Sayr qilamiz", "Kofe ichamiz", "Kino ko'ramiz",
          "Sovg'a olaman", "Birga ovqat pishiramiz", "Telefonda gaplashamiz",
          "Birga rasmga tushamiz", "Yulduzlarga qaraymiz"]

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

DAILY_Q = [
    "Juftingizga minnatdorlik bildiradigan 3 narsa yozing.",
    "Juftingizning qaysi odati sizga eng yoqadi?",
    "Birgalikda qilmoqchi bo'lgan eng katta orzuingiz nima?",
    "Juftingizni eng baxtli ko'rgan lahzangiz qaysi?",
    "Agar sizda bir kun vaqt bo'lsa, uni qanday o'tkazardingiz?",
    "Juftingizga hali aytmasdan his qilayotgan so'zingiz bormi?",
    "Sizning eng sevimli xususiyatingiz — juftingizning fikricha qaysi?",
    "Kelajakdagi uyingiz qanday bo'lishini xohlaysiz?",
    "Birgalikda o'tgan eng yoqimli kuningizni eslang.",
    "Siz uchun sevgi — bu nima?",
    "Bizning eng kuchli tomonimiz qanday?",
    "Bugun birga nima qilsak, ajoyib kun bo'lardi?",
    "Juftingizdan o'rganadigan narsangiz bormi?",
    "Qaysi musiqa bizning hikoyamizni aks ettiradi?",
    "Bir yildan keyin o'zingizni qayerda tasavvur qilasiz?",
    "Bugun juftingizni kulg'izadigan hazil yozing.",
    "Bizning eng zo'r odatimiz qaysi deb o'ylaysiz?",
    "Juftingizga bir sovg'a olsangiz, nima olardingiz?",
]

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

THEMES = [
    # --- bepul ---
    ("classic", "Klassik"), ("love", "Sevgi \u2764\ufe0f"),
    ("sunset", "Quyosh \U0001F305"), ("mint", "Yalpiz \U0001F343"),
    ("marmar", "Marmar \U0001F90D"),
    # --- premium \U0001F48E ---
    ("night", "Tun \U0001F319"), ("gold", "Oltin \u2b50"),
    ("ocean", "Okean \U0001F30A"), ("royal", "Shohona \U0001F451"),
    ("aurora", "Shimol yog\'dusi \U0001F30C"), ("blossom", "Gulzor \U0001F338"),
    ("velvet", "Baxmal \U0001F377"), ("sky", "Osmon \u2601\ufe0f"),
    ("neon", "Neon \u2728"), ("paper", "Qog'oz \U0001F4DC"),
]
PREMIUM_THEMES = {"night", "gold", "ocean", "royal", "aurora", "blossom", "velvet",
                  "sky", "neon", "paper"}

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

SUPPORT = os.environ.get("SUPPORT_CONTACT", "@pulim_more")

WELCOME = (
    "💌 <b>Yarashamiz</b>\n\n"
    "Arazni chiroyli tugating.\n\n"
    "📱 <b>Barcha imkoniyatlar Ilovada:</b>\n"
    "• ✍️ Xat yozish va yuborish\n"
    "• 🎮 Juftlik o'yinlari\n"
    "• 🔥 Kunlik seriya\n"
    "• 📖 Xotiralar va 🌱 bog'\n\n"
    "Pastdagi <b>📱 Ilovani ochish</b> tugmasini bosing.\n\n"
    "⚠️ Muammo bo'lsa: " + SUPPORT
)

# WEBAPP_URL (yoki Vercel domeni) aniqlanmasa — Ilova tugmasisiz rejim
WELCOME_NO_APP = (
    "💌 <b>Yarashamiz</b>\n\n"
    "Arazni chiroyli tugating.\n\n"
    "✍️ «Xat yozish» — uzr yoki sevgi xatingizni yozing.\n"
    "Havolani juftingizga yuboring, u javob beradi.\n\n"
    "⚠️ Muammo bo'lsa: " + SUPPORT
)

PRIVACY = (
    "🔒 <b>Maxfiylik</b>\n\n"
    "• Xatlaringiz va o'yin javoblaringiz faqat siz va juftingiz uchun.\n"
    "• Ma'lumotlar uchinchi shaxslarga sotilmaydi va berilmaydi.\n"
    "• Xat havolasi — maxfiy: uni faqat o'zingiz ishonadigan odamga yuboring.\n"
    "• Ma'lumotlaringizni o'chirishni xohlasangiz, " + SUPPORT + " ga yozing.\n\n"
    "Botdan foydalanishda rozilik bildirasiz."
)

HELP = ("<b>Qanday ishlaydi?</b>\n\n"
        "1. «✍️ Xat yozish» — uzr yoki sevgi xatingizni yozing.\n"
        "2. Uchrashuv taklifini tanlang va havolani juftingizga yuboring.\n"
        "3. U xatni ochadi va javob beradi.\n"
        "4. Yarashgach, «🎮 O'yinlar» bo'limida birga o'ynab ball to'playsiz.\n\n"
        "/menu — bosh menyu\n/cancel — bekor qilish\n/help — yordam\n"
        "/invite — do'stlarni taklif qilish (sovg'alar bor)\n"
        "/reminders — eslatmalarni yoqish/o'chirish\n"
        "/privacy — maxfiylik\n/feedback — fikr va taklif\n\n"
        "⚠️ Muammo bo'lsa: " + SUPPORT)

import base64  # noqa: E402
import datetime as dt  # noqa: E402
import html  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402

from aiogram.filters import Command, CommandObject, CommandStart, StateFilter  # noqa: E402
from aiogram.fsm.context import FSMContext  # noqa: E402
from aiogram.fsm.state import State, StatesGroup  # noqa: E402
from aiogram.types import (CallbackQuery, InlineKeyboardButton as IB,  # noqa: E402
                            InlineKeyboardMarkup as IM, KeyboardButton,
                            LabeledPrice, Message, PreCheckoutQuery,
                            ReplyKeyboardMarkup, WebAppInfo)

import store as st  # noqa: E402
from store import GAMES  # noqa: E402

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage(redis=ARedis.from_url(os.environ["REDIS_URL"])))


def reset_storage():
    """Serverless: har chaqiruv YANGI event loop yaratadi.

    Redis asyncio klienti yaratilgan loopga bog'lanadi. Yangi loopda eski
    klient ishlamaydi -> FSM state o'qilmaydi/yozilmaydi va handler
    topilmaydi (birinchi matn "yo'qoladi"). Har chaqiruvda yangilaymiz.
    """
    try:
        # Dispatcher.storage read-only, lekin RedisStorage.redis oddiy atribut
        dp.storage.redis = ARedis.from_url(os.environ["REDIS_URL"])
    except Exception as e:  # noqa: BLE001
        print("[reset_storage]", e, flush=True)


# ============================ XATO HANDLERI =============================
@dp.errors()
async def on_error(event):
    """Xatoni foydalanuvchiga ko'rsatmaymiz — Redis'ga yozamiz (diagnostika)."""
    exc = event.exception
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print("[error]", tb[-1500:], flush=True)
    try:
        st.r.set("ybot:lasterror", tb[-1200:])
    except Exception:  # noqa: BLE001
        pass
    try:
        u = None
        if event.update.message:
            u = event.update.message.from_user.id
        elif event.update.callback_query:
            u = event.update.callback_query.from_user.id
            try:
                await event.update.callback_query.answer()   # spinner osilib qolmasin
            except Exception:  # noqa: BLE001
                pass
        if u:
            # faqat tushunarli xabar - ichki xato matni foydalanuvchiga chiqmaydi
            await bot.send_message(u, "⚠️ Kutilmagan xatolik yuz berdi. "
                                      "Qayta urinib ko'ring yoki " + SUPPORT + " ga yozing.")
    except Exception:  # noqa: BLE001
        pass
    return True

today = lambda: st.today()  # noqa: E731  (mahalliy sana, UTC emas)
mission_of_day = lambda: MISSIONS[st.now().date().toordinal() % len(MISSIONS)]  # noqa: E731
dq_of_day = lambda: DAILY_Q[st.now().date().toordinal() % len(DAILY_Q)]  # noqa: E731


# ============================= KO'RINISHLAR =============================
def main_kb():
    """Bot chatida faqat Ilova tugmasi - qolgan hammasi ilova ichida."""
    if not URL:            # WEBAPP_URL aniqlanmasa Telegram xato beradi
        return None
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Ilovani ochish",
                        web_app=WebAppInfo(url=f"{URL}/"))],
    ])


def menu_kb(u):
    rows = [[IB(text="✍️ Xat yozish", callback_data="new")]]
    if st.pair_of(u):
        rows.append([IB(text="🎮 O'yinlar", callback_data="games")])
    rows += [[IB(text="📊 Hisobim", callback_data="stats"),
              IB(text="💌 Xotiralar", callback_data="lib")],
             [IB(text="🏆 Yutuqlar", callback_data="badges")],
             [IB(text="💎 Premium", callback_data="prem")]]
    return IM(inline_keyboard=rows)


def offer_kb(sel):
    rows = [[IB(text=("✅ " if o in sel else "") + o, callback_data=f"o:{i}")]
            for i, o in enumerate(OFFERS)]
    # foydalanuvchi o'zi yozgan takliflar
    customs = [x for x in sel if x not in OFFERS]
    for i, o in enumerate(customs):
        rows.append([IB(text="✅ " + o, callback_data=f"x:{i}")])
    rows.append([IB(text="➕ O'zim yozaman", callback_data="ox")])
    return IM(inline_keyboard=rows + [[IB(text="Tayyor", callback_data="done")]])


def theme_kb(u):
    return IM(inline_keyboard=[[IB(text=name + (" 🔒" if not theme_ok(t, u) else ""),
                                   callback_data=f"th:{t}")] for t, name in THEMES])


def open_letter_kb(lid, link):
    btn = KeyboardButton(text="💌 Xatni ochish",
                         web_app=WebAppInfo(url=f"{URL}/?d={link}&l={lid}"))
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[btn]])


def theme_ok(theme, u):
    return theme not in PREMIUM_THEMES or st.is_prem(u)


def games_view(u):
    p = st.pair_of(u)
    if not p:
        return None, None
    o, rows = st.other(p, u), []
    txt = "Bugungi o'yinlar. Ball faqat ikkalangiz ham o'ynasangiz beriladi.\n\n"
    for g, gg in GAMES.items():
        me, him = st.done(p[0], g, u), st.done(p[0], g, o)
        name = gg["name"] + (" 💎" if gg.get("prem") else "")
        txt += f"{name}: siz {'✅' if me else '⏳'}, juftingiz {'✅' if him else '⏳'}\n"
        if not me:
            lock = bool(gg.get("prem")) and not st.is_prem(u)
            rows.append([IB(text=("🔒 " if lock else "") + gg["name"],
                            callback_data=f"go:{g}")])
    return txt + f"\nJuftlik bali: {st.get_pts(p[0])}", IM(
        inline_keyboard=rows or [[IB(text="Premium 💎", callback_data="prem")]])


def profile_view(u):
    ps = st.profile_stats(u)
    p = ps["pair"]
    pts, days = ps["pts"], "—"
    if p and ps["since"]:
        days = max(0, (int(st.now().timestamp()) - ps["since"]) // 86400)
    st_, prem = ps["streak"], ps["prem"]
    tip = TIPS[st.now().date().toordinal() % len(TIPS)]
    return (f"📊 <b>Hisobingiz</b>\n\n"
            f"🔥 Ketma-kunlik seriya: <b>{st_}</b> kun\n"
            f"⭐ Juftlik bali: <b>{pts}</b>\n"
            f"❤️ Birga kunlar: <b>{days}</b>\n"
            f"💎 Premium: <b>{'faol' if prem else 'yo‘q'}</b>"
            + (f" ({ps['prem_days']} kun qoldi)" if prem else "") + "\n\n"
            f"💡 <i>{tip}</i>")


def badges_view(u):
    p = st.pair_of(u)
    pts = st.get_pts(p[0]) if p else 0
    letters = st.count_letters(u)
    st_ = st.streak(u)
    items = [("✉️ Birinchi xat", letters >= 1), ("❤️ Yarashtiruvchi", bool(p)),
             ("🔥 3 kunlik seriya", st_ >= 3), ("🔥 7 kunlik seriya", st_ >= 7),
             ("🔥 30 kunlik seriya", st_ >= 30), ("⭐ 100 ball", pts >= 100),
             ("⭐ 500 ball", pts >= 500), ("💎 Premium a'zosi", st.is_prem(u))]
    txt = "🏆 <b>Yutuqlar</b>\n\n" + "\n".join(
        f"{'✅' if ok else '⬜'} {name}" for name, ok in items)
    return txt, IM(inline_keyboard=[[IB(text="🎮 O'yinlar", callback_data="games")]])


def library_view(u):
    rows = st.my_library(u)
    if not rows:
        return "💌 Xotiralar bo'sh. Birinchi xatingizni yozing!"
    out = ["💌 <b>Xotiralar</b>\n"]
    for i, x in enumerate(rows):
        d = dt.datetime.fromtimestamp(x["ts"] + st.TZ_OFFSET * 3600).strftime("%d.%m")
        who = "siz →" if x["sender"] == u else "→ siz"
        out.append(f"{i+1}. {d} {who} «{html.escape(x['text'][:40])}…»")
    return "\n".join(out) + "\n\n<b>Premium</b> bilan xotiralar cheksiz saqlanadi 💎"


def premium_view(u):
    if st.is_prem(u):
        return (f"💎 <b>Premium faol</b> — {st.prem_days(u)} kun qoldi.\n\n"
                "Cheksiz xat, AI yordamchi, barcha shablonlar va o'yinlar sizniki.")
    return ("💎 <b>Premium</b> nima beradi?\n"
            "• ✍️ Cheksiz xat (bepulda kuniga 3)\n"
            "• ✨ Haqiqiy AI xat yozadi (Gemini) — uzr, sevgi, uchrashuv\n"
            "• 🎨 Maxsus xat shablonlari (Tun, Oltin)\n"
            "• 🎮 Qo'shimcha o'yin: Sevgi kvizi\n"
            "• 💌 Xotiralar cheksiz saqlanadi\n\n"
            f"Narx: <b>{PRICES['month']} ⭐</b> (oy) yoki "
            f"<b>{PRICES['year']} ⭐</b> (1 yil + 2 oy)\n\n"
            f"🎁 Juftingizga sovg'a: <b>{PRICES['gift']} ⭐</b> ({GIFT_DAYS} kun)")


def prem_kb():
    return IM(inline_keyboard=[
        [IB(text=f"⭐ {PRICES['month']} — 1 oy", callback_data="buy:month"),
         IB(text=f"⭐ {PRICES['year']} — 1 yil + 2 oy", callback_data="buy:year")],
        [IB(text=f"🎁 {PRICES['gift']} ⭐ — {GIFT_DAYS} kunlik sovg'a", callback_data="buy:gift")]])


def rem_kb(on):
    return IM(inline_keyboard=[[
        IB(text=("✅ 🔔 Yoqilgan" if on else "🔔 Yoqish"), callback_data="rem:1"),
        IB(text=("✅ 🔕 O'chirilgan" if not on else "🔕 O'chirish"), callback_data="rem:0")]])


def rem_text(on):
    return ("🔔 <b>Eslatmalar</b>\n\n"
            + ("Yoqilgan: har kuni kunlik savol, missiya va seriya eslatmasi keladi."
               if on else
               "O'chirilgan: kundalik eslatmalar kelmaydi. Botga o'zingiz kirib "
               "o'ynashingiz mumkin."))


def invite_text(u, username):
    n, ok = st.refs(u), st.refs_ok(u)
    nxt = next((k for k in sorted(st.REF_PREM) if k > ok), None)
    tip = (f"Keyingi sovg'a: <b>{nxt} ta tasdiqlangan taklif</b> → "
           f"{st.REF_PREM[nxt]} kun premium" if nxt else "Barcha sovg'alarni oldingiz 🎉")
    link = f"https://t.me/{username}?start=ref_{u}" if username else \
        "Havola mavjud emas — BOT_USERNAME sozlanmagan"
    return ("🎁 <b>Do'stlaringizni taklif qiling</b>\n\n"
            f"Har bir taklif uchun: <b>+{st.REF_BALL} ball</b> "
            "(juftligingizga qo'shiladi)\n"
            "3 ta taklif — <b>7 kun premium</b>\n"
            "10 ta taklif — <b>30 kun premium</b>\n"
            "(sovg'a taklif qilgan odam birinchi xat yozganda beriladi)\n\n"
            f"🔗 Sizning havolangiz:\n{link}\n\n"
            f"👥 Havolani bosganlar: <b>{n}</b> · "
            f"birinchi xat yozganlar: <b>{ok}</b>\n{tip}")


def qidx(g, step):
    qs = {"ab": AB, "wh": WHO, "qz": QZ}[g]
    return (st.now().date().toordinal() + step) % len(qs)


# ============================= FSM HOLATLAR =============================
class W(StatesGroup):
    text = State()
    offers = State()
    theme = State()
    ai_sit = State()
    ai_words = State()
    own_offer = State()     # O'z taklifini yozish
    dq = State()


# ============================= HANDLERLAR ===============================
@dp.message(CommandStart())
async def start(m: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    arg = command.args or ""

    if arg.startswith("l_"):
        lid = arg[2:]
        L = st.letter(lid)
        if not L:
            return await m.answer("Xat topilmadi.")
        if L["sender"] == m.from_user.id:
            return await m.answer(
                "Bu sizning xatingiz 💌\n\nUni Ilovada ko'rishingiz va dizaynini\n"
                "o'zgartirishingiz mumkin.",
                reply_markup=main_kb())
        if st.is_blocked(m.from_user.id, L["sender"]):
            return await m.answer("Bu yuboruvchidan xat olmaslikni tanlagansiz.")
        if L["receiver"] and L["receiver"] != m.from_user.id:
            return await m.answer("Bu xat allaqachon boshqa odamga tegishli 🙂")
        if not URL:
            # Ilova sozlanmagan bo'lsa ham xat matni ko'rinsin
            return await m.answer("Sizga xat bor 💌\n\n«" + html.escape(L["text"]) +
                                  "»\n\nTaklif: " +
                                  html.escape(", ".join(L["offers"])))
        st.seen(lid, m.from_user.id)     # shikoyat qilish huquqi uchun
        payload = base64.urlsafe_b64encode(json.dumps(
            {"t": L["text"], "o": L["offers"], "theme": L["theme"]}).encode()).decode()
        return await m.answer("Sizga xat bor 💌",
                              reply_markup=open_letter_kb(lid, payload))

    if arg.startswith("gift_"):
        days = st.use_gift(arg[5:], m.from_user.id)
        if days:
            st.touch(m.from_user.id)
            return await m.answer(f"🎁 Sovg'a qabul qilindi! Sizga <b>{days} kun</b> "
                                  "premium berildi 💎",
                                  reply_markup=menu_kb(m.from_user.id))
        return await m.answer("Bu sovg'a allaqachon ishlatilgan yoki yaroqsiz.")

    if arg.startswith("ref_"):
        ref = arg[4:]
        if ref.isdigit() and st.set_ref(m.from_user.id, int(ref)):
            try:
                await bot.send_message(
                    int(ref),
                    "🎉 Sizning havolangiz orqali yangi odam keldi!\n"
                    f"U birinchi xatini yozganda <b>+{st.REF_BALL} ball</b> olasiz.")
            except Exception:  # noqa: BLE001
                pass

    st.touch(m.from_user.id)
    await m.answer(WELCOME if URL else WELCOME_NO_APP,
                   reply_markup=main_kb() or menu_kb(m.from_user.id))


@dp.message(F.web_app_data)
async def reply(m: Message):
    try:
        r = json.loads(m.web_app_data.data or "{}")
    except Exception:  # noqa: BLE001
        return await m.answer("Ma'lumot noto'g'ri. Ilovani qayta oching.")
    u, a = m.from_user.id, str(r.get("a") or "")
    L = st.letter(r.get("l"))
    if not L:
        return await m.answer("Xat topilmadi.")
    sender = L["sender"]
    if sender == u:
        return await m.answer("Bu o'z xatingiz 🙂")
    # bloklangan yuboruvchidan kelgan xatga javob berilmaydi
    if a != "report" and st.is_blocked(u, sender):
        return await m.answer("Siz bu yuboruvchidan xat olmaslikni tanlagansiz.")
    # xat allaqachon boshqa odam tomonidan qabul qilingan bo'lsa
    if L["receiver"] and L["receiver"] != u:
        return await m.answer("Bu xat allaqachon boshqa odamga tegishli 🙂")
    if a == "reply":
        txt = str(r.get("t") or "").strip()[:300]
        if not txt:
            return await m.answer("Bo'sh javob yuborilmadi.")
        st.touch(u)
        await bot.send_message(
            sender,
            "💬 <b>Javob keldi</b>\n\n" + html.escape(txt)
            + "\n\nDavom ettirish uchun javob yozing.",
            reply_markup=menu_kb(sender))
        return await m.answer("✅ Javobingiz yuborildi.")
    if a == "stop":
        st.block(u, sender)
        return await m.answer("Tushunarli. Bu yuboruvchidan boshqa xat kelmaydi.")
    if a == "heart":
        st.touch(u)
        await bot.send_message(sender, "💝 Sizga yurak yuborildi! Javobingizni kutmoqda.")
        return await m.answer("💝 Yurak yuborildi.")
    if a == "yes":
        refused = None
        with st.lock(f"yes:{L['id']}") as ok:
            if not ok:
                return await m.answer("⏳ Bir oz kuting, qayta urinib ko'ring.")
            fresh = st.letter(L["id"]) or L
            if fresh["receiver"] == u:
                # takroriy bosish: holat o'zgarmaydi, xabar ikki marta ketmaydi
                return await m.answer("Allaqachon qabul qilingan ✅")
            p_u, p_s = st.pair_of(u), st.pair_of(sender)
            # juftlik faqat bitta bo'ladi: ikkinchi "yarashamiz" ma'lumotni buzmasin
            if p_u and st.other(p_u, u) != sender:
                refused = "Siz allaqachon boshqa juftlik bilan ulangansiz ❤️"
            elif p_s and st.other(p_s, sender) != u:
                refused = "Bu odam allaqachon juftlikda 🙂"
                try:
                    await bot.send_message(sender, "Javob: bu odam allaqachon juftlikda 🙂")
                except Exception:  # noqa: BLE001
                    pass
            else:
                if not p_u:
                    st.add_pair(sender, u)
                st.set_receiver(L["id"], u)
                st.touch(u)
                st.touch(sender)
        if refused:
            return await m.answer(refused)
        await bot.send_message(sender, "Javob: <b>yarashamiz</b> 🎉 "
                               f"Taklif: {html.escape(str(r.get('o') or ''))}\n"
                               "Endi birga o'ynashingiz mumkin.",
                               reply_markup=menu_kb(sender))
        return await m.answer("Yarashdingiz 🎉 Endi birga o'ynang.",
                              reply_markup=menu_kb(u))
    if a == "report":
        if not st.has_seen(L["id"], u):
            return await m.answer("Xat topilmadi. Uni havola orqali qayta oching.")
        if not st.add_report(L["id"], u, sender, L.get("text", "")):
            return await m.answer("Siz bu xatni allaqachon shikoyat qilgansiz.")
        # faqat haqiqiy qabul qiluvchi uchun blok; begona (forward) shikoyat
        # yuboruvchini bloklamaydi — faqat admin tekshiradi
        accepted = L["receiver"] == u
        if accepted:
            st.block(u, sender)
        if ADMIN_ID:
            try:
                await bot.send_message(
                    int(ADMIN_ID),
                    "⚠️ <b>Shikoyat</b>\n"
                    f"Kimdan: <code>{sender}</code>\nKimga: <code>{u}</code>\n"
                    f"Qabul qilingan: {'yo‘q' if L['receiver'] != u else 'ha'}\n"
                    f"Xat #{L['id']}: {html.escape(str(L.get('text') or '')[:200])}")
            except Exception:  # noqa: BLE001
                pass
        return await m.answer(
            "⚠️ Shikoyat qabul qilindi. Bu yuboruvchidan boshqa xat kelmaydi va "
            "admin xabardor qilindi." if accepted else
            "⚠️ Shikoyat qabul qilindi. Admin tekshiradi; bu yuboruvchidan xat "
            "qabul qilmasangiz bo'ladi.")
    if a == "later":
        await bot.send_message(sender, "Javob: hali tayyor emas, keyinroq ⏳")
        return await m.answer("Xabar yuborildi ⏳")
    await m.answer("Javobingiz yuborildi.")


@dp.message(Command("menu"))
async def menu_cmd(m: Message):
    await m.answer("Asosiy menyu:", reply_markup=menu_kb(m.from_user.id))


@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(HELP)


@dp.message(Command("privacy"))
async def privacy_cmd(m: Message):
    await m.answer(PRIVACY)


@dp.message(Command("feedback"))
async def feedback_cmd(m: Message):
    """Foydalanuvchi fikri — adminga yuboriladi va Redis'da saqlanadi."""
    txt = (m.text or "").partition(" ")[2].strip()[:500]
    if not txt:
        return await m.answer("Fikringizni yozing: <code>/feedback xabar matni</code>")
    try:
        st.r.rpush("feedback", json.dumps(
            {"u": m.from_user.id, "t": txt, "ts": int(time.time())}))
        st.r.ltrim("feedback", -500, -1)
    except Exception:  # noqa: BLE001
        pass
    if ADMIN_ID:
        try:
            await bot.send_message(int(ADMIN_ID),
                                   f"📩 Feedback <code>{m.from_user.id}</code>:\n"
                                   + html.escape(txt))
        except Exception:  # noqa: BLE001
            pass
    await m.answer("Rahmat! Fikringiz adminga yuborildi 🙏")


@dp.message(Command("invite"))
async def invite_cmd(m: Message):
    me = await bot.get_me()
    await m.answer(invite_text(m.from_user.id, me.username))


@dp.message(Command("reminders"))
async def reminders_cmd(m: Message):
    on = st.reminders_on(m.from_user.id)
    await m.answer(rem_text(on), reply_markup=rem_kb(on))


@dp.callback_query(F.data.startswith("rem:"))
async def rem_cb(c: CallbackQuery):
    on = c.data[4:] == "1"
    st.set_reminders(c.from_user.id, on)
    await c.message.edit_text(rem_text(on), reply_markup=rem_kb(on))
    await c.answer("Yoqildi ✅" if on else "O'chirildi 🔕")


@dp.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Bekor qilindi.", reply_markup=menu_kb(m.from_user.id))


@dp.message(Command("admin"))
async def admin(m: Message):
    if not ADMIN_ID or str(m.from_user.id) != ADMIN_ID:
        return
    s = st.admin_stats()
    await m.answer(f"📊 <b>Admin hisobot</b>\n\n"
                   f"👥 Foydalanuvchilar: <b>{s['users']}</b> "
                   f"(bugun +{s['new_today']})\n"
                   f"⚡️ Bugun faol: <b>{s['active_today']}</b>\n"
                   f"❤️ Juftliklar: <b>{s['pairs']}</b> (bugun +{s['pairs_today']})\n"
                   f"💌 Xatlar: <b>{s['letters']}</b> (bugun {s['letters_today']})\n"
                   f"🎁 Referral: <b>{s['refs']}</b>\n"
                   f"📩 Feedback: <b>{s['feedback']}</b> · "
                   f"⚠️ Shikoyat: <b>{s['reports']}</b>\n"
                   f"💎 Premium: <b>{s['prem_active']}</b> faol / {s['prem']} jami")


# ------------------------------ XAT OQIMI -------------------------------
def variants(sit, words):
    return [t.replace("{w}", (words or "").strip() or FALLBACK) for t in AI_TPL[sit]]


async def reward_ref(u):
    """Foydalanuvchi birinchi xatini yozganda referrerni mukofotlaydi."""
    got = st.claim_reward(u)
    if not got:
        return
    ref, n = got
    p = st.pair_of(ref)
    txt = "🎉 Taklifingizdan yangi odam birinchi xatini yozdi!"
    txt += (f"\n⭐ Juftlikka +{st.REF_BALL} ball qo'shildi." if p else
            "\n⭐ Juftlik topilgach ball qo'shiladi.")
    if n in st.REF_PREM:
        txt += (f"\n💎 {n} ta tasdiqlangan taklif — "
                f"{st.REF_PREM[n]} kunlik premium sovg'a!")
    try:
        await bot.send_message(ref, txt)
    except Exception:  # noqa: BLE001
        pass


async def do_new(m: Message, state: FSMContext):
    u = m.from_user.id
    if st.count_today_letters(u, st.day_start_ts()) >= DAILY_LIMIT and not st.is_prem(u):
        return await m.answer("Bugungi bepul limit (3 xat) tugadi. Ertaga yozing yoki "
                              "💎 Premium oling — cheksiz xat yoziladi.")
    await state.set_state(W.text)
    await m.answer("Xat matnini yozing (300 belgigacha). Uzr so'rang, samimiy bo'ling.",
                   reply_markup=IM(inline_keyboard=[
                       [IB(text="✨ AI yordamchi bilan yozish", callback_data="ai")]]))


@dp.callback_query(F.data == "new")
async def new(c: CallbackQuery, state: FSMContext):
    await do_new(c.message, state)
    await c.answer()


@dp.message(W.text, F.text)
async def got_text(m: Message, state: FSMContext):
    await state.update_data(text=m.text[:300], offers=[], own_count=0)
    await state.set_state(W.offers)
    await m.answer("Qanday uchrashuv taklif qilasiz? (bir nechtasini tanlang)",
                   reply_markup=offer_kb([]))


@dp.callback_query(W.offers, F.data.startswith("o:"))
async def toggle(c: CallbackQuery, state: FSMContext):
    try:
        o = OFFERS[int(c.data[2:])]
    except (ValueError, IndexError):
        return await c.answer()
    sel = list((await state.get_data()).get("offers") or [])
    sel = [x for x in sel if x != o] if o in sel else sel + [o]
    await state.update_data(offers=sel)
    await c.message.edit_reply_markup(reply_markup=offer_kb(sel))
    await c.answer()


@dp.callback_query(W.offers, F.data == "ox")
async def own_offer_start(c: CallbackQuery, state: FSMContext):
    """O'z taklifini yozish. Bepul: 1 ta, premium: cheksiz."""
    d = await state.get_data()
    if not st.is_prem(c.from_user.id) and int(d.get("own_count", 0)) >= 1:
        return await c.answer(
            "Bepul versiyada 1 ta o'z taklifingiz. Premium — cheksiz 💎",
            show_alert=True)
    # state W.offers da qoladi - keyingi matn o'z taklifi bo'ladi
    await c.message.answer(
        "✍️ Taklifingizni yozing (40 belgigacha).\n\nYozgach takliflar ro'yxati qaytadi.")
    await c.answer()


@dp.message(W.offers, F.text)
async def own_offer_text(m: Message, state: FSMContext):
    """W.offers holatida yozilgan har qanday matn = o'z taklifi."""
    txt = m.text.strip()[:40]
    if not txt:
        return await m.answer("Bo'sh bo'lmasin. Qaytadan yozing:")
    d = await state.get_data()
    sel = list(d.get("offers") or [])
    if txt not in sel:
        sel.append(txt)
    await state.update_data(offers=sel, own_count=int(d.get("own_count", 0)) + 1)
    await state.set_state(W.offers)
    await m.answer(f"✅ «{txt}» qo'shildi", reply_markup=offer_kb(sel))





@dp.callback_query(W.offers, F.data.startswith("x:"))
async def own_offer_del(c: CallbackQuery, state: FSMContext):
    """O'z taklifini o'chirish."""
    d = await state.get_data()
    sel = list(d.get("offers") or [])
    customs = [x for x in sel if x not in OFFERS]
    i = int(c.data[2:])
    if 0 <= i < len(customs):
        sel.remove(customs[i])
        await state.update_data(offers=sel)
    await c.message.edit_reply_markup(reply_markup=offer_kb(sel))
    await c.answer()


@dp.callback_query(W.offers, F.data == "done")
async def finish(c: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    if not d.get("offers"):
        return await c.answer("Kamida bitta taklif tanlang", show_alert=True)
    await state.set_state(W.theme)
    await c.message.answer("Xat qanday ko'rinishda bo'lsin?",
                           reply_markup=theme_kb(c.from_user.id))
    await c.answer()


@dp.callback_query(W.theme, F.data.startswith("th:"))
async def theme(c: CallbackQuery, state: FSMContext):
    t = c.data[3:]
    if not theme_ok(t, c.from_user.id):
        return await c.answer("Bu shablon premium uchun 💎", show_alert=True)
    d = await state.get_data()
    if not d.get("text") or not d.get("offers"):
        await state.clear()
        return await c.answer("Xat matni topilmadi. Qaytadan boshlang: /menu",
                              show_alert=True)
    lid = st.add_letter(c.from_user.id, d["text"], d["offers"], t)
    await state.clear()
    me = await bot.get_me()
    st.touch(c.from_user.id)
    await reward_ref(c.from_user.id)
    await c.message.answer("Xat tayyor. Havolani juftingizga o'zingiz yuboring:\n"
                           f"https://t.me/{me.username}?start=l_{lid}")
    await c.answer()


# ------------------------------- AI -------------------------------------
@dp.callback_query(F.data == "ai")
async def ai_start(c: CallbackQuery, state: FSMContext):
    if not st.is_prem(c.from_user.id):
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
    sit = d["sit"]
    await m.answer("✨ Yozyapman...", reply_markup=None)
    # avval haqiqiy AI (Gemini); u holda shablon bilan davom etamiz
    real = await asyncio.to_thread(ai_helper.compose, sit, m.text)
    vs = ([real] if real else []) + variants(sit, m.text)
    await state.update_data(variants=vs, vi=0)
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
    vs = d.get("variants") or []
    if not vs:
        return await c.answer("Variant topilmadi, qaytadan boshlang", show_alert=True)
    i = int(d.get("vi", 0)) % len(vs)
    await state.update_data(text=vs[i][:300], offers=[], own_count=0)
    await state.set_state(W.offers)
    await c.message.answer("Zo'r! Endi uchrashuv taklifini tanlang:",
                           reply_markup=offer_kb([]))
    await c.answer()


# ------------------------------- MENYU ----------------------------------
@dp.callback_query(F.data == "games")
async def games_cb(c: CallbackQuery):
    t, kb = games_view(c.from_user.id)
    if not t:
        return await c.answer("Avval xat orqali yarashing ❤️", show_alert=True)
    await c.message.answer(t, reply_markup=kb)
    await c.answer()


@dp.callback_query(F.data == "stats")
async def stats_cb(c: CallbackQuery):
    st.touch(c.from_user.id)
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
                           reply_markup=None if st.is_prem(c.from_user.id) else prem_kb())
    await c.answer()


@dp.callback_query(F.data == "menu")
async def menu_cb(c: CallbackQuery):
    await m_answer_menu(c)
    await c.answer()


async def m_answer_menu(c: CallbackQuery):
    await c.message.answer("Asosiy menyu:", reply_markup=menu_kb(c.from_user.id))


# ------------------------------ TO'LOV ----------------------------------
@dp.callback_query(F.data.startswith("buy:"))
async def buy(c: CallbackQuery):
    kind = c.data[4:]
    if kind not in ("month", "year", "gift"):
        return await c.answer()
    payload = (f"gift:{c.from_user.id}" if kind == "gift"
               else f"prem:{kind}:{c.from_user.id}")
    await bot.send_invoice(
        chat_id=c.from_user.id, title="Yarashamiz Premium 💎",
        description={"month": "1 oylik premium: cheksiz xat, AI yordamchi.",
                     "year": "1 yillik premium (2 oy bepul).",
                     "gift": f"Juftingizga {GIFT_DAYS} kunlik premium sovg'a."}[kind],
        payload=payload, provider_token="", currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=PRICES[kind])])
    await c.answer()


@dp.pre_checkout_query()
async def pre(q: PreCheckoutQuery):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def paid(m: Message):
    parts = (m.successful_payment.invoice_payload or "").split(":")
    if parts[0] == "prem" and len(parts) >= 3 and parts[1] in PREMIUM_DAYS:
        try:
            uid = int(parts[2])
        except ValueError:
            return
        days = PREMIUM_DAYS[parts[1]]
        st.add_prem(uid, days)
        await m.answer(f"💎 Premium faollashdi! {days} kunlik "
                       "imtiyozlar sizniki.")
    elif parts[0] == "gift":
        token = st.make_gift(GIFT_DAYS)
        me = await bot.get_me()
        await m.answer("🎁 Sovg'a tayyor! Havolani juftingizga yuboring:\n"
                       f"https://t.me/{me.username}?start=gift_{token}")


# --------------------------- PASTKI TUGMALAR ----------------------------
@dp.message(F.text == "✍️ Xat yozish", StateFilter(None))
async def btn_new(m: Message, state: FSMContext):
    await do_new(m, state)


@dp.message(F.text == "🎮 O'yinlar")
async def btn_games(m: Message):
    t, kb = games_view(m.from_user.id)
    await m.answer(t or "Avval xat orqali yarashing ❤️", reply_markup=kb)


@dp.message(F.text == "📊 Hisobim")
async def btn_stats(m: Message):
    st.touch(m.from_user.id)
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
                   reply_markup=None if st.is_prem(m.from_user.id) else prem_kb())


# ============================== O'YINLAR ================================
def ab_kb(i):
    q, a, b = AB[i]
    return q, IM(inline_keyboard=[[IB(text=a, callback_data=f"abo:{i}:0"),
                                    IB(text=b, callback_data=f"abo:{i}:1")]])


async def ask_match(msg, g, step):
    gg = GAMES[g]
    q = {"wh": WHO, "qz": QZ}[g][qidx(g, step)]
    a, b = ("Men", "U") if g == "wh" else ("Ha", "Yo'q")
    await msg.answer(f"{step + 1}/{gg['n']}. {q}",
                     reply_markup=IM(inline_keyboard=[
                         [IB(text=a, callback_data=f"mg:{g}:{step}:0"),
                          IB(text=b, callback_data=f"mg:{g}:{step}:1")]]))


async def after(u, p, g):
    o = st.other(p, u)
    if not st.done(p[0], g, o):
        hint = ("💬 Bugungi savolga javob bering — juftingiz javobini keyin ko'rasiz."
                if g == "kq" else f"Juftingiz «{GAMES[g]['name']}» o'yinini o'ynadi. "
                                  "Siz ham o'ynang.")
        return await bot.send_message(
            o, hint,
            reply_markup=IM(inline_keyboard=[[IB(text="🎮 O'yinlar", callback_data="games")]]))
    # ikki marta (masalan, ilova + bot) yuborilsa ball ikki marta qo'shilmasin
    with st.lock(f"after:{p[0]}:{g}:{st.today()}") as ok:
        if not ok:
            return
        scored = f"scored:{p[0]}:{g}:{st.today()}"
        if st.r.get(scored):
            return
        d1, d2, gg = st.get(p[0], g, u), st.get(p[0], g, o), GAMES[g]
        if d1 is None or d2 is None:
            return
        if gg["mode"] == "talk":
            pts = 5
        elif gg["mode"] == "match":
            pts = 2 * sum(d1[i] == d2[i] for i in range(gg["n"]))
            if d1 == d2:
                pts += 5
        elif g == "ab":
            pts = sum(2 * (d1[i][1] == d2[i][0]) + 2 * (d2[i][1] == d1[i][0])
                      + (d1[i][0] == d2[i][0]) for i in range(gg["n"]))
        else:
            pts = 10
        st.add_pts(p[0], pts)
        st.r.set(scored, 1, ex=2 * 86400)   # faqat ball muvaffaqiyatli qo'shilgach
        st.touch(u)
        if g == "kq":
            # ikkalasi ham javob bergan — bir-birining javobini ko'rsatamiz
            await bot.send_message(u, "💬 Juftingizning bugungi javobi:\n\n"
                                   f"«{html.escape(str(d2[0]))}»\n\n+{pts} ball 🎯")
            await bot.send_message(o, "💬 Juftingizning bugungi javobi:\n\n"
                                   f"«{html.escape(str(d1[0]))}»\n\n+{pts} ball 🎯")
            return
        await asyncio.gather(*[
            bot.send_message(x, f"«{gg['name']}» natijasi: {pts} ball 🎯 "
                                "Ikkalangiz ham qatnashdingiz.")
            for x in (u, o)], return_exceptions=True)


@dp.callback_query(F.data.startswith("go:"))
async def go(c: CallbackQuery, state: FSMContext):
    g = c.data[3:]
    u, p = c.from_user.id, st.pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval xat orqali yarashing ❤️", show_alert=True)
    gg = GAMES.get(g)
    if not gg:
        return await c.answer()
    if gg.get("prem") and not st.is_prem(u):
        return await c.answer("Bu o'yin premium uchun 💎", show_alert=True)
    if st.done(p[0], g, u):
        return await c.answer("Bugun o'ynagansiz ✅")
    if gg["mode"] == "mission":
        await c.message.answer("Bugungi missiya:\n" + mission_of_day(),
                               reply_markup=IM(inline_keyboard=[
                                   [IB(text="✅ Bajardim", callback_data="msd")]]))
    elif gg["mode"] == "talk":
        await state.set_state(W.dq)
        await c.message.answer("💬 Bugungi savol:\n\n" + dq_of_day() +
                               "\n\nJavobingizni matn ko'rinishida yozing:")
    elif gg["mode"] == "guess":
        q, kb = ab_kb(qidx(g, 0))
        await c.message.answer("Avval o'zingiz tanlang, keyin juftingiz nimani "
                               "tanlashini toping.\n\n" + q, reply_markup=kb)
    else:
        await ask_match(c.message, g, 0)
    await c.answer()


@dp.message(W.dq, F.text)
async def dq_answer(m: Message, state: FSMContext):
    u, p = m.from_user.id, st.pair_of(m.from_user.id)
    if not p:
        await state.clear()
        return await m.answer("Juftingiz topilmadi.")
    if st.done(p[0], "kq", u):
        await state.clear()
        return await m.answer("Bugun allaqachon javob bergansiz ✅")
    st.put(p[0], "kq", u, [m.text[:300]])
    await state.clear()
    await m.answer("Javobingiz qabul qilindi! Juftingizning javobini u ham javob "
                   "bergach ko'rasiz 💬")
    await after(u, p, "kq")


@dp.callback_query(F.data.startswith("abo:"))
async def ab_own(c: CallbackQuery):
    _, i, o = c.data.split(":")
    u, p = c.from_user.id, st.pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    d = st.get(p[0], "ab", u) or []
    if int(i) != qidx("ab", len(d)) or int(o) not in (0, 1):
        if int(i) == qidx("ab", len(d) - 1) and len(d) > 0:
            return await c.answer()          # allaqachon javob berilgan
        return await c.answer("Savol yangilandi. /menu → 🎮 O'yinlar",
                              show_alert=True)
    q, a, b = AB[int(i)]
    await c.message.edit_text(f"{q}\nSiz: {(a, b)[int(o)]}. Juftingiz nimani tanlaydi?",
                              reply_markup=IM(inline_keyboard=[
                                  [IB(text=a, callback_data=f"abg:{i}:{o}:0"),
                                   IB(text=b, callback_data=f"abg:{i}:{o}:1")]]))
    await c.answer()


@dp.callback_query(F.data.startswith("abg:"))
async def ab_guess(c: CallbackQuery):
    _, i, o, g = c.data.split(":")
    u, p = c.from_user.id, st.pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    d = st.get(p[0], "ab", u) or []
    if int(i) != qidx("ab", len(d)) or int(o) not in (0, 1) or int(g) not in (0, 1):
        if int(i) == qidx("ab", len(d) - 1) and len(d) > 0:
            return await c.answer()          # allaqachon javob berilgan
        return await c.answer("Savol yangilandi. /menu → 🎮 O'yinlar",
                              show_alert=True)
    d.append([int(o), int(g)])
    st.put(p[0], "ab", u, d)
    if len(d) < GAMES["ab"]["n"]:
        q, kb = ab_kb(qidx("ab", len(d)))
        await c.message.edit_text(q, reply_markup=kb)
    else:
        await c.message.edit_text("Tayyor ✅")
        await after(u, p, "ab")
    await c.answer()


@dp.callback_query(F.data.startswith("mg:"))
async def mg(c: CallbackQuery):
    _, g, step, x = c.data.split(":")
    u, p = c.from_user.id, st.pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    gg = GAMES.get(g)
    if not gg or gg.get("mode") not in ("match",):
        return await c.answer()
    if gg.get("prem") and not st.is_prem(u):
        return await c.answer("Bu o'yin premium uchun 💎", show_alert=True)
    try:
        step, x = int(step), int(x)
    except ValueError:
        return await c.answer()
    if x not in (0, 1):
        return await c.answer()
    d = st.get(p[0], g, u) or []
    if len(d) != step:
        if step == len(d) - 1:
            return await c.answer()          # takroriy bosish
        return await c.answer("Savol yangilandi. /menu → 🎮 O'yinlar",
                              show_alert=True)
    d.append(x)
    st.put(p[0], g, u, d)
    if len(d) < gg["n"]:
        q = {"wh": WHO, "qz": QZ}[g][qidx(g, len(d))]
        a, b = ("Men", "U") if g == "wh" else ("Ha", "Yo'q")
        await c.message.edit_text(f"{len(d) + 1}/{gg['n']}. {q}",
                                  reply_markup=IM(inline_keyboard=[
                                      [IB(text=a, callback_data=f"mg:{g}:{len(d)}:0"),
                                       IB(text=b, callback_data=f"mg:{g}:{len(d)}:1")]]))
    else:
        await c.message.edit_text("Tayyor ✅")
        await after(u, p, g)
    await c.answer()


@dp.callback_query(F.data == "msd")
async def ms_done(c: CallbackQuery, state: FSMContext):
    u, p = c.from_user.id, st.pair_of(c.from_user.id)
    if not p:
        return await c.answer("Avval yarashing ❤️", show_alert=True)
    if st.done(p[0], "ms", u):
        return await c.answer("Bugun allaqachon bajarilgan ✅", show_alert=True)
    st.put(p[0], "ms", u, {"ok": 1})
    await state.clear()
    await c.message.edit_text("Missiya bajarildi ✅")
    await after(u, p, "ms")
    await c.answer()


# ============================== ESLATMALAR ==============================
async def run_reminders():
    """Cron tomonidan chaqiriladi. (u, xabar) juftliklar ro'yxatini qaytaradi."""
    out = []
    now_h = st.now().hour          # mahalliy vaqt (UTC+5), UTC emas
    for u in st.users():
        if not st.reminders_on(u):      # foydalanuvchi o'chirib qo'ygan
            continue
        p = st.pair_of(u)
        if not p:
            continue
        if now_h >= 19 and not st.sent(u, "ms") and not st.done(p[0], "ms", u):
            out.append((u, "🌙 Bugungi missiya bajarilmagan. "
                           "Juftingizni bir gaplashib, birga qiling!"))
            st.mark(u, "ms")
        if now_h >= 12 and not st.sent(u, "kq") and not st.done(p[0], "kq", u):
            out.append((u, f"💬 Bugungi savol: {dq_of_day()}\n\nJavob yozing — "
                           "juftingizning javobini ko'rasiz."))
            st.mark(u, "kq")
        row = st.streak_row(u)
        if row and int(row.get("n", 0)) >= 3 and row.get("last") != today() \
                and not st.sent(u, "st"):
            out.append((u, f"🔥 Seriyani buzma! {row['n']} kunlik seriyangiz bor. "
                           "Bugun bir o'yin o'ynang."))
            st.mark(u, "st")
    return out


# ============================== ZAXIRA ==================================
@dp.message()
async def fallback(m: Message, state: FSMContext):
    """Mos handler topilmagan xabarlar (matn, sticker, rasm...).

    Foydalanuvchi javobsiz qolmasin: yo'l ko'rsatamiz.
    """
    cur = await state.get_state()
    if m.text and m.text.startswith("/"):
        return await m.answer("Bunday komanda yo'q. /menu yoki /help dan foydalaning.",
                              reply_markup=menu_kb(m.from_user.id))
    if cur:
        return await m.answer("Iltimos, matn ko'rinishida yozing yoki /cancel bilan "
                              "bekor qiling.")
    if URL:
        return await m.answer("Barcha imkoniyatlar Ilovada 👇\n"
                              "Pastdagi «📱 Ilovani ochish» tugmasini bosing.",
                              reply_markup=main_kb())
    await m.answer("Asosiy menyu 👇", reply_markup=menu_kb(m.from_user.id))
