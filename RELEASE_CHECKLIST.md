# Yarashamiz — Release QA Checklist

**Sana:** 2026-10-31 · **Branch:** `main` · **HEAD:** `79b64f1` (Merge PR #45)
**Muhit:** Python 3.11.2 · aiogram 3.31.0 · redis 8.1.0 · fakeredis 2.40.0 · Node v24.15.0
**Prod:** https://yarashamiz-two.vercel.app

> 🔒 Maxfiylik: bu faylda hech qanday token, parol yoki ID **qiymati** yo'q — faqat `true/false` va «bor/yo'q». Kod o'zgartirilmadi, commit/push qilinmadi.

## 1. Tekshiruv natijalari

| # | Tekshiruv | Natija | Izoh |
|---|---|---|---|
| 1 | `python3 tests/smoke.py` | ✅ **287/287 o'tdi, ❌ 0** | exit code `0`; 35 bo'lim; jami 288 ta `✅` satr = 287 test + 1 yakuniy xulosa («Barcha tekshiruvlar o'tdi»); 2 marta yuritildi — natija bir xil (repeatable) |
| 2 | `python3 -m py_compile bot.py store.py api/*.py` | ✅ exit `0` | 8 fayl sintaksis tekshirildi: `bot.py`, `store.py`, `api/app.py`, `api/channel.py`, `api/check.py`, `api/cron.py`, `api/setup.py`, `api/webhook.py` — xato yo'q |
| 3 | `node --check mini_app/app.js` | ✅ exit `0` | Node v24.15.0, JS sintaksis xatosi yo'q |
| 4 | `diff -r mini_app public/mini_app` | ✅ **farq YO'Q** | 3 fayl 1:1 bir xil: `app.js`, `index.html`, `style.css` (Vercel `public/` nusxasi sinxron) |
| 5 | `GET /api/check` → `ok` | ✅ `true`, `warnings: []` | HTTP 200, ogohlantirish yo'q — barcha kritik env o'rnatilgan |
| 6 | `GET /api/check` → `BOT_TOKEN` | ✅ `true` (bor) | qiymat yozilmadi |
| 7 | `GET /api/check` → `REDIS_URL` | ✅ `true` (bor) | sxema `rediss://` — Upstash TLS talabiga mos |
| 8 | `GET /api/check` → `CHANNEL_ID` | ✅ `true` (bor) | qiymat yozilmadi |
| 9 | `GET /api/check` → `ADMIN_ID` | ⚠️ bor, **lekin javobda ochiq qiymat** | ID qiymati bu faylga yozilmadi; pastdagi «Xavflar»ga qarang |
| 10 | `GET /api/check` → `CRON_SECRET` | ✅ `true` (bor) | qiymat yozilmadi |
| 11 | `GET /api/check` → `SETUP_KEY` | ✅ `true` (bor) | `/api/check?bot=1` kalitsiz → **HTTP 401** = himoya ishlaydi |
| 12 | `GET /api/check` → `GEMINI_API_KEY` | ✅ `true` (bor) | AI funksiyalari uchun |
| 13 | `GET /api/check` → narx/limit | ℹ️ `TRIAL_DAYS=3`, `PRICE_MONTH=50`, `PRICE_YEAR=500`, `PRICE_GIFT=80` | hammasi «standart» = env'da override qilinmagan |
| 14 | `GET /api/app` | ✅ HTTP 200 | `{"ok": true, "service": "yarashamiz app api", "bot": "yarashamiz_bot", "webapp": "https://yarashamiz-two.vercel.app/mini_app"}` |
| 15 | `GET /mini_app/` | ✅ HTTP 200 | Mini App statik fayllari prod'da xizmat qilinyapti |
| 16 | Webhook / `getMe` (`/api/check?bot=1`) | ⏳ tekshirilmadi | `SETUP_KEY` talab qiladi — qo'lda: `/api/check?bot=1&s=<SETUP_KEY>` (kalitni faylga yozmang) |
| 17 | `tests/smoke.py` logida `[error] ValueError: secret-internal-detail` | ✅ kutilgan (xato emas) | 8-bo'lim («Xato handleri») ataylab xato chiqarib, maxfiy ma'lumot oshkor bo'lmasligini tekshiradi; `❌` yo'q |

**Umumiy xulosa:** 17 qatordan **15 tasi avtomatik bajarildi**, 1 tasi qo'lda (`SETUP_KEY` kerak), 1 tasi izoh (kutilgan log). Holat **yashil** — 287/287 test, 0 xato, sintaksis/JS toza, prod API'lar 200. Relizni bloklovchi muammo **topilmadi**.

## 2. Xavflar / e'tibor talab qiladigan joylar

| Daraja | Topilma | Tavsiya |
|---|---|---|
| 🟡 O'rtacha | `/api/check` autentifikatsiyasiz ochiq va `ADMIN_ID` ni **qiymat** sifatida qaytaradi (+ `token_bot_id`, `token_len`). Fayl izohida «faqat bor/yo'q» deyilgan — hujjat bilan kod mos emas | `ADMIN_ID` ni `bool`ga aylantirish yoki butun endpoint'ni `SETUP_KEY` ortiga yashirish. Relizni bloklamaydi |
| 🔵 Past | `content/channel_week_draft.json` ish papkasida **untracked** | Egasi qaror qilsin: commit qilinadi yoki o'chiriladi (men tegmadim) |
| 🔵 Past | Smoke test faqat `fakeredis` bilan ishlaydi — haqiqiy Upstash'ni tekshirmaydi | 3-qadamda jonli Redis `ping` o'lchovi (`?ping=1`) |

## 3. Qayta yuritish (repro)

```bash
cd /workspace
python3 -m pip install -r requirements.txt fakeredis
python3 tests/smoke.py 2>&1 | tail -5      # 287 ✅, 0 ❌ kutiladi
python3 -m py_compile bot.py store.py api/*.py && echo PY_OK
node --check mini_app/app.js && echo JS_OK
diff -r mini_app public/mini_app && echo NO_DIFF
curl -s https://yarashamiz-two.vercel.app/api/check   # ok:true, warnings:[]
curl -s https://yarashamiz-two.vercel.app/api/app     # ok:true
```

## 4. Ertangi chiqish uchun qolgan 3–5 qadam

1. **2 ta akkaunt bilan qo'lda oqim (eng muhim).** A akkaunt → B ga xat yozadi → B havola orqali ochadi → javob beradi → juftlash → ochilish sahnasi + eslatma. Qabul mezoni: har ikkala tomonda xat ko'rinadi, takroriy juftlash/xat bloklanadi, kunlik limit ishlaydi.
2. **Kanal posti va cron'lar.** `/api/channel` (kunlik post) va `/api/cron` (eslatmalar) ni `SETUP_KEY` bilan qo'lda trigger qilib ko'rish; keyin `?bot=1` bilan `webhook_ok:true`, `pending_update_count` past va `last_error_message` bo'sh ekaniga ishonch hosil qilish.
3. **Pul oqimi: trial + promo-kod + sovg'a.** 3 kunlik trial tugashi, promo-kod faqat 1 marta ishlashi, gift narxi (80) va to'lov himoyasi (takroriy «to'landi» bosilmasligi) — 35-bo'lim testlari yashil, lekin jonli Telegram Stars/to'lov oqimini qo'lda tasdiqlash kerak.
4. **Upstash backup + limit.** Export/backup olib qo'yish, Redis `ping` kechikishi (`?ping=1`), buyruqlar soni va bepul limitga yaqinlashmaganini tekshirish; `rediss://` saqlanib qolganini tasdiqlash.
5. **Hardening + rollback tayyorgarligi.** `/api/check` dan `ADMIN_ID` ni yashirish (kichik patch, alohida PR), hamda Vercel'da oldingi deployment ID'ni yozib qo'yish — nosozlik bo'lsa 1 klikda qaytarish uchun.

---
*Bu fayl faqat QA natijalarini qayd etadi; repo kodi va git tarixi o'zgartirilmagan.*
