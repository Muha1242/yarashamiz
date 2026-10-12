# Yarashamiz boti

Telegram Mini App: arazlashgan juftliklar uchun xat yozish, o'yinlar, kunlik
check-in va vaqt kapsulasi.

> **Eslatma:** loyiha **Node.js** (serverless funksiyalar) asosida. Avvalgi README
> `bot.py` va `requirements.txt` haqida yozgan edi — bunday fayllar repoda yo'q.

## Arxitektura

```
public/yarashamiz.html   Mini App (bitta fayl: HTML + CSS + JS)
api/*.js                 Vercel serverless endpointlar
  me, play, checkin, letter_new, letter_get, respond, capsule_new, webhook
lib/core.js              Umumiy mantiq: auth, Redis, Telegram API, o'yin qoidalari
```

Frontend API'ni `?api=<APP_URL>` parametri orqali topadi va
`<APP_URL>/api/<nom>` ga POST qiladi. Har bir so'rov `initData` bilan
imzolanadi (`lib/core.js` dagi `auth()` HMAC-SHA256 orqali tekshiradi).

## Muhit o'zgaruvchilari

| Nomi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ha | @BotFather'dan olingan token |
| `APP_URL` | ha | Deploy manzili, masalan `https://<loyiha>.vercel.app` |
| `UPSTASH_REDIS_REST_URL` | ha* | Upstash Redis REST manzili |
| `UPSTASH_REDIS_REST_TOKEN` | ha* | Upstash Redis REST tokeni |
| `WEBHOOK_SECRET` | tavsiya | Webhook'ni begona POST'lardan himoyalaydi |

\* Vercel KV ishlatilsa `KV_REST_API_URL` / `KV_REST_API_TOKEN` ham qabul qilinadi.

## Deploy (Vercel)

1. Reponi Vercel'ga ulang. `public/` avtomatik statik, `api/` esa funksiya bo'ladi.
2. Yuqoridagi muhit o'zgaruvchilarini Project Settings > Environment Variables
ga qo'shing.
3. Deploy qiling.
4. Telegram webhook'ni o'rnating:

```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=$APP_URL/api/webhook" \
  -d "secret_token=$WEBHOOK_SECRET"
```

5. Mini App manzili: `$APP_URL/yarashamiz.html`

> GitHub Pages faqat statik HTML uchun ishlaydi — `api/` funksiyalari u yerda
> ishlamaydi, shuning uchun API alohida joyda (Vercel/Render) turishi kerak.

## Lokal ishlab chiqish

```bash
npm install
npx vercel dev
```

`?api=` parametrisiz ochilsa, frontend ichidagi `MOCK` ma'lumotlar bilan
ishlaydi (server kerak emas).
