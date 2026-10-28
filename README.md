# Yarashamiz boti v3.1 💌

Sevishganlarni yarashtirish uchun Telegram boti — **Vercel'da bepul** ishlaydi.

- 🤖 **aiogram 3.x** + **Upstash Redis** (ma'lumotlar va FSM)
- ✨ **Haqiqiy AI** (Google Gemini) — kalit bo'lmasa shablon bilan ishlaydi
- ☁️ **Webhook** rejimi — kompyuter yoki server kerak emas
- 📱 **3D Mini App** — konvert ochilishi, yurak, konfetti

---

## Imkoniyatlar

| Bo'lim | Tafsilot |
|---|---|
| ✍️ **Xat yozish** | 300 belgigacha, **15 shablon** (5 bepul + 10 premium; yangi «Marmar 🤍», «Neon ✨», «Qog'oz 📜») |
| ✨ **AI yordamchi** | Gemini bilan haqiqiy xat: *uzr, sog'inch, sevgi, minnatdorchilik, uchrashuv* |
| ❤️ **Juftlik** | Mini App'da «Yarashamiz» bosilsa ikkalasi ham xabar oladi |
| 🎮 **O'yinlar (5 xil)** | *A yoki B*, *Kim ko'proq?*, *Kunlik missiya*, **💬 Kunlik savol**, **Sevgi kvizi** 💎 |
| 🔥 **Kunlik seriya** | Streak + avtomatik eslatmalar (Vercel Cron) |
| 💌 **Xotiralar** | Yozgan/olgan xatlar tarixi |
| 🖼 **Rasm kartochka** | Xatni PNG rasm qilib saqlash (Mini App) |
| 🎁 **Referral** | Do'st taklif qilish: +10 ball, 3 ta — 7 kun, 10 ta — 30 kun premium |
| ⏳ **Vaqt kapsulasi** 💎 | Kelajakdagi sanaga (1 oy–1 yil) xat qulflash; vaqti kelganda cron xabar yuboradi |
| 🎟️ **Sevgi biletlari** | Juftingizga vaucher («Kino», «Massaj»...), bir marta ishlatiladi (bepul: 1/kun) |
| 🔔 **Eslatma sozlamalari** | `/reminders` — yoqish/o'chirish (Ilovada ham) |
| ⚠️ **Shikoyat** | Xatni shikoyat qilish: yuboruvchi bloklanadi, admin xabardor |
| 🏆 **Yutuqlar** | Badge tizimi |
| 💎 **Premium** | Telegram Stars (XTR) + juftlikka sovg'a |
| 📊 **/admin** | Statistika: DAU, yangi, xat/juftlik bugun, referral, shikoyat (faqat `ADMIN_ID` uchun) |

---

## Fayl tuzilishi

```
bot.py            - botning to'liq kodi (aiogram 3.x)
store.py          - Upstash Redis ma'lumotlar qatlami
ai_helper.py      - Google Gemini AI yordamchisi
requirements.txt  - aiogram>=3.13, redis>=5.0
vercel.json       - cron jadvali
api/
  webhook.py      - Telegram yangilanishlarini qabul qiladi
  setup.py        - webhookni ro'yxatdan o'tkazadi
  cron.py         - kunlik eslatmalar (Vercel Cron)
mini_app/         - Mini App manbasi (3D)
public/mini_app/  - Vercel xizmat qiladigan nusxa
legacy/           - eski Node.js versiyasi (ishlatilmaydi)
```

---

## 🚀 Vercel'ga joylash

### 1. Upstash Redis (bepul)
[upstash.com](https://upstash.com) → **Create Database**

Keyin **ikki xil** manzil kerak bo'ladi:

| Nima | Qayerdan | Format |
|---|---|---|
| `REDIS_URL` | **Connect** → **Redis Connect** → `redis://` yoki `rediss://` | `rediss://default:xxx@xxx.upstash.io:6379` |

> ⚠️ **Diqqat:** `UPSTASH_REDIS_REST_URL` (REST) **ishlamaydi** — bot TCP ulanish
> ishlatadi. Upstash panelida **`REDIS_URL`** (yoki `REDIS_TLS_URL`) ni oling.

### 2. Muhit o'zgaruvchilari

Vercel → **Settings → Environment Variables**:

| Nomi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ✅ | @BotFather'dan |
| `REDIS_URL` | ✅ | Upstash TCP manzili (`rediss://...`) |
| `WEBAPP_URL` | tavsiya | `https://<loyiha>.vercel.app/mini_app` (bo'lmasa avtomatik aniqlanadi) |
| `SETUP_KEY` | ✅ | `/api/setup` ni qulflash uchun (bo'lmasa endpoint yopiq) |
| `TZ_OFFSET` | ixtiyoriy | Mahalliy vaqt siljishi, standart `5` (Toshkent, UTC+5) |
| `GEMINI_API_KEY` | ixtiyoriy | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `ADMIN_ID` | ixtiyoriy | Sizning Telegram ID (admin panel + shikoyatlar uchun) |
| `BOT_USERNAME` | ixtiyoriy | Ilovada referral havolasi uchun (masalan `yarashamiz_bot`) |
| `WEBHOOK_SECRET` | ixtiyoriy | Webhook'ni himoyalash |
| `CRON_SECRET` | ixtiyoriy | `/api/cron` ni qulflash (`Authorization: Bearer ...`) |
| `CRON_MAX_MSGS` | ixtiyoriy | Bir cron'da yuboriladigan maksimal xabar (standart `600`) |
| `CRON_CONCURRENCY` | ixtiyoriy | Parallel yuborish (standart `12`) |
| `CRON_RATE` | ixtiyoriy | Global tezlik, xabar/soni (standart `28`, Telegram ~30/s) |

**Premium narxlari** (ixtiyoriy):

| Nomi | Standart |
|---|---|
| `PRICE_MONTH` | `50` ⭐ |
| `PRICE_YEAR` | `500` ⭐ (1 yil + 2 oy) |
| `PRICE_GIFT` | `80` ⭐ |
| `GIFT_DAYS` | `30` kun |

### 3. Deploy qiling

### 4. Webhook'ni o'rnating

Brauzerda bir marta:
```
https://<loyiha>.vercel.app/api/setup?s=<SETUP_KEY>
```
`webhook set: ...` javobini ko'rsangiz — tayyor.

### 5. Eslatmalar (Vercel Cron)
`vercel.json` da sozlangan — kuniga bir marta `/api/cron` chaqiriladi
(15:00 UTC = **20:00** O'zbekiston). Qo'lda sinash: `/api/cron`.

---

## 💎 Premium

| Tarif | Narx | Muddat |
|---|---|---|
| Oylik | **50 ⭐** | 30 kun |
| Yillik | **500 ⭐** | 425 kun (1 yil + 2 oy) |
| Juftlikka sovg'a | **80 ⭐** | 30 kun |

**Premium beradi:** cheksiz xat · AI yordamchi · 10 premium shablon · Sevgi kvizi ·
⏳ vaqt kapsulasi · cheksiz sevgi biletlari · cheksiz xotiralar.

**Bepul:** kuniga 3 xat, 5 shablon, o'yinlar, kuniga 1 sevgi bileti.

**Sozlash:** @BotFather → `/mybots` → botni tanlang → **Payments** → **Telegram Stars** yoqilgan bo'lsin.

---

## 💻 Lokal ishlash

```bash
export BOT_TOKEN="123456:ABC..."
export REDIS_URL="rediss://default:xxx@xxx.upstash.io:6379"
export WEBAPP_URL="https://<host>/mini_app"
python bot.py
```

---

## Komandalar

| Komanda | Vazifa |
|---|---|
| `/start` | Salom + bosh menyu |
| `/menu` | Asosiy menyu |
| `/help` | Yordam |
| `/invite` | Do'stlarni taklif qilish havolasi + sovg'alar |
| `/reminders` | Kunlik eslatmalarni yoqish/o'chirish |
| `/privacy` | Maxfiylik siyosati |
| `/feedback` | Fikr/taklif (adminga boradi) |
| `/cancel` | Joriy amalni bekor qilish |
| `/admin` | Statistika (faqat `ADMIN_ID`) |
| `/diag` | 🩺 Diagnostika: Redis, token, webhook, oxirgi xato (faqat `ADMIN_ID`) |

`/api/setup` ni bir marta ochganda bot menyusi, qisqa tavsif va to'liq tavsif ham
avtomatik o'rnatiladi.

---

## 🆘 «Ilovani botdan oching» / «Xatolik: auth» bo‘lsa

Mini App ochiladi, lekin har bo‘limda `auth` xatosi chiqsa — `/api/app` 401
qaytaryapti. Endi ilovaning o‘zi **sababni** ko‘rsatadi (`sabab: bad_hash`,
`no_token`, `expired`, `no_init`...). Tekshirish tartibi:

1. **Deploy qaysi branch'dan?** PR #34 merge qilinmagan bo‘lsa, production eski
   kod bilan ishlaydi. `main` ga merge → Vercel **Redeploy**.
2. `https://<domen>/api/check` → `ok: true`, `BOT_TOKEN: true`,
   `REDIS_URL_scheme: "rediss://"`, `WEBAPP_URL` shu domenga teng.
3. `https://<domen>/api/check?bot=1&s=<SETUP_KEY>` → eng muhim diagnostika:
   - `getMe.ok: true` va `getMe.username` — token **haqiqiy**;
   - `webhook.url` = `https://<domen>/api/webhook`;
   - `webhook.last_error_message` bo‘sh bo‘lishi kerak;
   - `token_bot_id` — token qaysi botga tegishli ekani (Mini App shu botdan
     ochilishi shart).
4. `https://<domen>/api/setup?s=<SETUP_KEY>` — bir marta (webhook + menyu).
5. Ilovani **botdagi** «📱 Ilovani ochish» tugmasidan oching — havoladan yoki
   brauzerdan ochilsa `initData` bo‘lmaydi (`no_init`).

| Sabab | Ma’nosi / yechim |
|---|---|
| `no_init` | Mini App botdan tashqarida ochilgan. Bot tugmasidan oching |
| `no_token` | Vercel'da `BOT_TOKEN` yo‘q yoki bo‘sh |
| `bad_hash` | `BOT_TOKEN` boshqa botga tegishli / oxirida bo‘sh joy / revoke qilingan |
| `no_hash` | So‘rov to‘liq kelmagan (proksi/CDN) — qayta urinib ko‘ring |
| `expired` | `initData` 3 kundan eski — botdan qayta oching |
| `no_user` | `user` maydoni yo‘q — Telegram mijozini yangilang |

### 🧊 Bot umuman javob bermayapti (qotib qolgan) bo‘lsa

1. `https://<domen>/api/check?bot=1` → `hint` maydoni sababni aytadi.
2. `getMe.ok: false` → token revoke qilingan yoki boshqa botga tegishli.
3. `webhook.last_error_message` da **Conflict** → boshqa joyda polling
   ishlayapti (lokal `python bot.py`, eski server) — uni to‘xtating, keyin
   `/api/setup?s=SETUP_KEY`.
4. `webhook.url` bo‘sh → `/api/setup?s=SETUP_KEY` bir marta.
5. `pending_update_count` o‘syapti → webhook 500 qaytaryapti: Vercel →
   Functions → Logs ni ko‘ring (`ybot:lasterror` Redis'da ham bor).
6. Upstash bepul limiti (10k buyruq/kun) tugagan bo‘lsa — handlerlar xato
   beradi; limitni oshiring.

Endi Redis (5s), `get_me` (6s) va AI (20s) uchun timeoutlar bor — bitta sekin
tashqi xizmat butun webhook'ni osiltirib qo‘ymaydi.

---

## 🧪 Sinov (offline)

Tashqi xizmatlarsiz — `fakeredis` bilan:

```bash
pip install -r requirements.txt fakeredis
python tests/smoke.py
```

Testlar: xat yaratish va kunlik limit, xat maxfiyligi, juftlik (ikki marta
juftlanmaslik), o'yin savollarining bot va Ilovada bir xil bo'lishi, ball
ikki marta qo'shilmasligi, eslatma vaqti (UTC+5), xato handleri, sovg'a va
to'liq xat yozish oqimi (FSM).

<!-- build: fsm-loop-fix -->
