# Yarashamiz boti — v3 💌

Sevishganlarni yarashtirish uchun Telegram boti: **xat yozish → havola →
Mini App orqali javob → juftlik o'yinlari va ball**.

- 🤖 **aiogram 3.x** (Python 3.10+)
- ☁️ **Vercel'da bepul** ishlaydi — kompyuter yoki server kerak emas (webhook rejimi)
- 💾 Baza — SQLite, **Upstash Redis**'da saqlanadi (bepul tarif yetarli)
- 📱 Mini App — `mini_app/` papkasi

---

## Imkoniyatlar

| Bo'lim | Tafsilot |
|---|---|
| ✍️ **Xat yozish** | 300 belgigacha, 4 xil taklif, **4 shablon** (Klassik, Sevgi ❤️, Tun 🌙, Oltin ⭐) |
| ✨ **AI yordamchi** | 5 holatda shablon asosida yozadi: *uzr, sog'inch, sevgi, minnatdorchilik, uchrashuv* |
| ❤️ **Juftlik** | Mini App'da «Yarashamiz» bosilsa ikkalasi ham xabar oladi |
| 🎮 **O'yinlar (4 xil)** | *A yoki B*, *Kim ko'proq?*, *Kunlik missiya*, **Sevgi kvizi** 💎 |
| 🔥 **Kunlik seriya** | Streak va eslatmalar |
| 💌 **Xotiralar** | Yozgan/olgan xatlar tarixi |
| 🏆 **Yutuqlar** | 8 xil badge |
| 💎 **Premium** | **Telegram Stars (XTR)** + juftlikka sovg'a |

---

## Fayl tuzilishi

```
bot.py            — botning to'liq kodi (aiogram 3.x)
fsm_store.py      — SQLite'ga asoslangan FSM (holat) saqlash
vstore.py         — Upstash Redis klienti + SQLite blob sinxronizatsiyasi
requirements.txt  — aiogram>=3.13
api/
  tg.py           — Vercel webhook (Telegram update'larini qabul qiladi)
  tg_setup.py     — webhook va komandalarni o'rnatadi
mini_app/         — Mini App manbasi (asosiy nusxa)
  index.html · style.css · app.js
public/mini_app/  — Vercel xizmat qiladigan nusxa
```

---

## 🚀 Vercel'ga joylash (tavsiya — bepul, kompyutersiz)

### 1. Upstash Redis oling (bepul)
1. [upstash.com](https://upstash.com) → **Create Database**
2. **REST API** bo'limidan `UPSTASH_REDIS_REST_URL` va `UPSTASH_REDIS_REST_TOKEN` ni oling

> Redis **majburiy**: Vercel'da fayl tizimi vaqtinchalik, SQLite bazasi shu yerda saqlanadi.

### 2. Vercel'ga muhit o'zgaruvchilarini qo'shing
Project → **Settings → Environment Variables**:

| Nomi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ✅ | @BotFather'dan |
| `WEBAPP_URL` | ✅ | Mini App manzili, masalan `https://<loyiha>.vercel.app/mini_app` |
| `UPSTASH_REDIS_REST_URL` | ✅ | Upstash'dan |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ | Upstash'dan |
| `WEBHOOK_SECRET` | tavsiya | Webhook'ni begona POST'lardan himoyalaydi |
| `SETUP_KEY` | ixtiyoriy | `/api/tg_setup` ni qulflash uchun |
| `CRON_SECRET` | ixtiyoriy | `/api/cron` ni qulflash uchun |
| `TZ_OFFSET` | ixtiyoriy | Mahalliy vaqt siljishi (standart `5` = UTC+5) |

### 3. Deploy qiling
Repo'ni Vercel'ga ulang yoki **Deploy** tugmasini bosing.

### 4. Webhook'ni o'rnating
Brauzerda bir marta oching:

```
https://<loyiha>.vercel.app/api/tg_setup
```

Javobda `"ok": true` ko'rsangiz — tayyor! Bu buyruq:
- `setWebhook` → `https://<loyiha>.vercel.app/api/tg`
- `setMyCommands` → `/start`, `/menu`, `/help`, `/cancel`

### 5. Mini App manzili
`https://<loyiha>.vercel.app/mini_app` — shuni `WEBAPP_URL` ga yozing.

### 6. Eslatmalar (Vercel Cron)
`vercel.json` da cron sozlangan — kuniga bir marta `/api/cron` chaqiriladi
(15:00 UTC = **20:00** O'zbekiston). U quyidagilarni yuboradi:

- 🌙 Bugungi missiya bajarilmagan bo'lsa
- 🔥 3+ kunlik seriya uzilib qolsa

Vaqtni o'zgartirish: `vercel.json` dagi `schedule` ni tahrirlang
(`0 15 * * *` = har kuni 15:00 UTC). Qo'lda sinash: `/api/cron`.

> ⚠️ Vercel **Hobby** tarifida cron kuniga **bir marta** ishlaydi — bu yetarli.

### 7. Eslatmalarni qo'lda sinash
Brauzerda: `https://<loyiha>.vercel.app/api/cron` → `{"ok": true, "job": "reminders"}`

---

## 💻 Lokal ishlash (long polling)

```bash
export BOT_TOKEN="123456:ABC..."
export WEBAPP_URL="https://<host>/mini_app"
python bot.py
```

Lokal rejimda Redis **shart emas** — baza `bot.db` faylida saqlanadi.
`python bot.py` long polling ishlatadi (Vercel esa webhook ishlatadi).

---

## ⚙️ Qanday ishlaydi (Vercel)

Vercel'da fon jarayoni yo'q, shuning uchun bot **webhook** rejimida ishlaydi:

```
Telegram  →  POST /api/tg
              │
              1. Redis'dan  bot.db  →  /tmp/bot.db      (pull)
              2. update aiogram Dispatcher orqali qayta ishlanadi
              3. /tmp/bot.db  →  Redis                   (push)
```

```
Vercel Cron  →  GET /api/cron   (kuniga 1 marta)
              │  reminders_once() — missiya va seriya eslatmalari
```

Holat (FSM) ham shu bazada saqlanadi (`fsm_store.py`) — shuning uchun
ko'p qadamli amallar (xat yozish, AI yordamchi) serverless'da ham ishlaydi.

---

## 📱 Mini App'ni boshqa joyda host qilish

`mini_app/` papkasidagi 3 ta faylni istalgan statik hostingga qo'yish mumkin
(GitHub Pages, Netlify). Muhim: **`index.html` ildizda** ochilishi kerak,
chunki bot havolani `{WEBAPP_URL}/?d=...&l=...` ko'rinishida yasaydi.

---

## 💎 Telegram Stars premium

| Tarif | Narx | Muddat |
|---|---|---|
| Oylik | **500 ⭐** | 30 kun |
| Yillik | **5000 ⭐** | 365 kun |
| Juftlikka sovg'a | **500 ⭐** | 30 kun |

**Premium beradi:** cheksiz xat, 2 qo'shimcha shablon (Tun, Oltin), Sevgi kvizi, AI yordamchi.

**Sozlash:** @BotFather → `/mybots` → botni tanlang → **Payments** → **Telegram Stars** yoqilgan bo'lsin.

---

## Eski bazadan migratsiya

`bot.py` ishga tushganda `pairs.ts`, `letters.theme`, `letters.receiver`
ustunlari **avtomatik** qo'shiladi (`try/except` orqali). Eski `bot.db` ni
o'chirish shart emas.

---

## 📌 Eslatma

Repo'da avvalgi **Node.js/Vercel** versiyasi ham qolgan (`api/*.js`, `lib/`,
`public/yarashamiz.html`, `scripts/`, `package.json`).
U **ishlatilmaydi** va `bot.py` ga ta'sir qilmaydi — eski avtomatik webhook
sozlamasi o'chirilgan. Xohlasangiz o'chirib tashlash mumkin.
