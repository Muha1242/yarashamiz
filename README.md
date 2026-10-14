# Yarashamiz boti — v3 (universal) 💌

Sevishganlarni yarashtirish uchun Telegram boti: **xat yozish → havola → Mini App
orqali javob → juftlik o'yinlari va ball**.

- 🤖 **aiogram 3.x** asosida (Python 3.10+)
- 💾 Ma'lumotlar bazasi — **SQLite** (`bot.db`, avtomatik yaratiladi)
- 📱 Mini App — `mini_app/` papkasidagi 3 ta statik fayl
- 📦 Qo'shimcha kutubxona **kerak emas** — faqat `aiogram`

---

## Imkoniyatlar

| Bo'lim | Tafsilot |
|---|---|
| ✍️ **Xat yozish** | 300 belgigacha matn, 4 xil taklif, **4 shablon** (Klassik, Sevgi ❤️, Tun 🌙, Oltin ⭐) |
| ✨ **AI yordamchi** | 5 holatda shablon asosida xat yozadi: *uzr, sog'inch, sevgi, minnatdorchilik, uchrashuv* |
| ❤️ **Juftlik** | Mini App'da «Yarashamiz» bosilsa ikkalasi ham xabar oladi, juftlik ochiladi |
| 🎮 **O'yinlar (4 xil)** | *A yoki B*, *Kim ko'proq?*, *Kunlik missiya*, **Sevgi kvizi** 💎 (premium) |
| 🔥 **Kunlik seriya** | Har kunlik kirish seriyasi (streak) va eslatmalar |
| 💌 **Xotiralar** | Yozgan/olgan xatlar tarixi |
| 🏆 **Yutuqlar** | 8 xil badge |
| 💎 **Premium** | **Telegram Stars (XTR)** bilan to'lov + juftlikka sovg'a |
| 🔔 **Eslatmalar** | Har soatda missiya/seriya eslatmasi (`reminders()`) |

---

## Fayl tuzilishi

```
bot.py                 — botning to'liq kodi (aiogram 3.x)
requirements.txt       — aiogram>=3.13
mini_app/
  index.html           — Mini App sahifasi (Telegram WebApp SDK ulangan)
  style.css            — gradient dizayn, yurak animatsiyasi
  app.js               — xatni ochish, javob yuborish, konfeti
bot.db                 — SQLite (birinchi ishga tushirishda avtomatik yaratiladi)
```

---

## O'rnatish va ishga tushirish

```bash
# 1. Kutubxonalar
pip install -r requirements.txt

# 2. Muhit o'zgaruvchilari
export BOT_TOKEN="123456:ABC..."          # @BotFather'dan
export WEBAPP_URL="https://<host>/mini_app"   # Mini App manzili (pastga qarang)

# 3. Ishga tushirish
python bot.py
```

### Muhit o'zgaruvchilari

| Nomi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ✅ ha | @BotFather'dan olingan token |
| `WEBAPP_URL` | ✅ ha | Mini App joylashgan manzil. Bot unga `/?d=...&l=...` qo'shadi |

> ⚠️ Bot **long polling** ishlatadi — VPS, Railway yoki Render kabi doimiy
> ishlaydigan serverda ishlashi kerak (Vercel/GitHub Pages faqat statik fayllar uchun).

---

## Mini App'ni host qilish

`mini_app/` papkasidagi 3 ta faylni istalgan statik hostingga joylang.
Muhim: **`index.html` ildizda ochilishi kerak**, chunki bot havolani
`{WEBAPP_URL}/?d=...&l=...` ko'rinishida yasaydi.

### 🅰️ GitHub Pages
1. `mini_app/` papkasini repo'ga push qiling
2. Settings → Pages → Branch: `main`, papka: `/ (root)`
3. Manzil: `https://<login>.github.io/<repo>/mini_app`

### 🅱️ Vercel / Netlify
1. `mini_app/` ni loyiha ildiziga qo'ying (yoki `public/` papkasiga)
2. Deploy qiling
3. Manzil: `https://<loyiha>.vercel.app`

### Muhim
- Manzil **HTTPS** bo'lishi shart — Telegram boshqasini qabul qilmaydi
- `WEBAPP_URL` oxirida `/` **qo'ymang** (bot o'zi qo'shadi)

---

## 💎 Telegram Stars premium

To'lov **Telegram Stars (XTR)** orqali ishlaydi — qo'shimcha to'lov provayderi
kerak emas (`provider_token=""`).

| Tarif | Narx | Muddat |
|---|---|---|
| Oylik | **500 ⭐** | 30 kun |
| Yillik | **5000 ⭐** | 365 kun |
| Juftlikka sovg'a | **500 ⭐** | 30 kun |

### Premium nima beradi
- ♾️ **Cheksiz xat** (bepul limit — kuniga 3 ta)
- 🎨 **2 qo'shimcha shablon** — Tun 🌙 va Oltin ⭐
- 🎮 **Sevgi kvizi** o'yini
- ✨ **AI yordamchi**

### Sozlash
1. @BotFather → `/mybots` → botni tanlang
2. **Payments** → **Telegram Stars** yoqilgan bo'lishi kerak
3. Botdagi **💎 Premium** tugmasi orqali to'lov amalga oshiriladi

---

## Komandalar

| Komanda | Vazifa |
|---|---|
| `/start` | Salom xabari + bosh menyu |
| `/menu` | Bosh menyu |
| `/help` | Yordam |
| `/cancel` | Joriy amalni bekor qilish |

### Bosh menyu tugmalari
`✍️ Xat yozish` · `🎮 O'yinlar` · `📊 Hisobim` · `💌 Xotiralar` · `🏆 Yutuqlar` · `💎 Premium`

---

## Eski bazadan migratsiya

`bot.py` ishga tushganda eski `bot.db` ga quyidagi ustunlar **avtomatik** qo'shiladi
(`try/except sqlite3.OperationalError` orqali):

- `letters.theme`
- `letters.receiver`
- `pairs.ts`

Ya'ni eski bazani o'chirish shart emas — bot uni o'zi yangilaydi.

---

## Eslatma (eski versiya)

Repo'da avvalgi **Node.js / Vercel** versiyasi ham saqlanib qolgan
(`api/`, `lib/`, `public/`, `package.json`, `scripts/`).
Ular bot v3 ga ta'sir qilmaydi — `bot.py` ulardan mustaqil ishlaydi.
