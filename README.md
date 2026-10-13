# Yarashamiz boti

Telegram Mini App: arazlashgan juftliklar uchun xat yozish, o'yinlar, kunlik
check-in va vaqt kapsulasi.

> **Eslatma:** loyiha **Node.js** (serverless funksiyalar) asosida. Avvalgi README
> `bot.py` va `requirements.txt` haqida yozgan edi — bunday fayllar repoda yo'q.

## Imkoniyatlar

- **Xat yozish** - bosqichma-bosqich sehrgar, tayyor shablon bilan
- **Juftlik** - xat havolasi orqali yarashish, bloklash/shikoyat
- **O'yinlar (7 xil)**
  - *A yoki B* - 5 savol: o'zingiz tanlaysiz va juftingiz tanlovini topasiz
  - *Kim ko'proq?* - 5 savol, bir xil javobga ball
  - *Kelajak xaritasi* - 6 savol, kelajak rejalaringiz mosligi foizda
  - *Sevgi tili testi* - 5 savol, qanday sevish turingizni aniqlaydi
  - *Sirli savollar* - 3 ta erkin javob, ikkalangiz tugatgach ochiladi
  - *Minnatdorchilik* - 3 ta samimiy minnatdorchilik yozasiz
  - *Kunlik missiya* - kichik vazifa, 10 ball
- **/start** - chiroyli rasm va menyu tugmasi bilan kutib oladi
- **Kunlik check-in** - kayfiyat belgilash + streak
- **Bog'imiz** - juftlik birgalikda ball to'plab o'stiradigan virtual bog'.
  Har kuni ikkalasi ham check-in qilsa bog'ga bitta gul qo'shiladi;
  ball oshgani sari o'simlik Urug' -> Nihol -> Yosh daraxt -> Gullagan
  daraxt -> Mevali daraxt -> Afsonaviy bog' bosqichlaridan o'tadi
- **Vaqt kapsulasi** - kelajakka xat (7/30/365 kun)
- **Tinchlanish mashqi** - nafas olish + 10 daqiqa pauza + «Men» tilida gapirish

## Arxitektura

```
public/yarashamiz.html   Mini App (bitta fayl: HTML + CSS + JS)
api/*.js                 Vercel serverless endpointlar
  me, play, checkin, letter_new, letter_get, respond, capsule_new
  webhook                Telegram /start buyruqlarini qabul qiladi
  setup                  Webhook va menyu tugmasini avtomatik o'rnatadi
lib/core.js              Umumiy mantiq: auth, Redis, Telegram API, o'yin qoidalari
```

Frontend API'ni `?api=<APP_URL>` parametri orqali topadi va
`<APP_URL>/api/<nom>` ga POST qiladi. Har bir so'rov `initData` bilan
imzolanadi (`lib/core.js` dagi `auth()` HMAC-SHA256 orqali tekshiradi).

## Muhit o'zgaruvchilari

| Nomi | Majburiy | Izoh |
|---|---|---|
| `BOT_TOKEN` | ha | @BotFather'dan olingan token |
| `APP_URL` | ha | Deploy manzili, masalan `https://loyiha.vercel.app`. **Protokolsiz ham bo'ladi** (`loyiha.vercel.app`) |
| `UPSTASH_REDIS_REST_URL` | ha* | Upstash Redis REST manzili |
| `UPSTASH_REDIS_REST_TOKEN` | ha* | Upstash Redis REST tokeni |
| `WEBHOOK_SECRET` | tavsiya | Webhook'ni begona POST'lardan himoyalaydi |
| `SETUP_KEY` | ixtiyoriy | `/api/setup` ni qulflash uchun. Bo'lmasa endpoint kalitsiz ishlaydi (u faqat o'z domenini sozlaydi, zarar yetkaza olmaydi) |

\* Vercel KV ishlatilsa `KV_REST_API_URL` / `KV_REST_API_TOKEN` ham qabul qilinadi.

> `APP_URL` berilmasa, kod `VERCEL_PROJECT_PRODUCTION_URL` yoki `VERCEL_URL` dan
automatik aniqlaydi. Agar u ham bo'lmasa, bot `/start` ga tushunarli xato
xabarini yuboradi.

## Deploy (Vercel)

1. Reponi Vercel'ga ulang. `public/` avtomatik statik, `api/` esa funksiya bo'ladi.
2. Project Settings > Environment Variables bo'limiga yuqoridagi
   o'zgaruvchilarni qo'shing.
3. Deploy qiling.
4. **Sozlash avtomatik bajariladi.** Deploy paytida Vercel `npm run build` ni
   ishga tushiradi (`scripts/vercel-setup.js`) va u o'zi:
   - `setWebhook` — Telegram'ni `/api/webhook` ga ulaydi
   - `setChatMenuButton` — chatda **"Yarashamiz"** menyu tugmasini o'rnatadi
     (Mini App'ga doimiy kirish tugmasi)

   Buning uchun faqat `BOT_TOKEN` bo'lishi kifoya. Vercel build loglarida
   `[setup] setWebhook: OK` qatorini ko'rasiz. Skript xato bersa ham deploy
   to'xtatilmaydi va u faqat production deployda ishlaydi (previewda emas).

   <details>
   <summary>Muqobil: brauzerda qo'lda sozlash</summary>

   ```
   https://<domen>/api/setup
   ```

   `SETUP_KEY` o'rnatilgan bo'lsa: `https://<domen>/api/setup?key=<SETUP_KEY>`

   Javobda `"ok": true` ko'rsangiz — hammasi tayyor. Javobdagi `before`
   maydoni o'zgarishdan OLDINGI webhook holatini ko'rsatadi (diagnostika uchun).
   </details>

<details>
<summary>Muqobil: qo'lda curl bilan</summary>

```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=$APP_URL/api/webhook" \
  -d "secret_token=$WEBHOOK_SECRET"

curl "https://api.telegram.org/bot$BOT_TOKEN/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d "{\"menu_button\":{\"type\":\"web_app\",\"text\":\"Yarashamiz\",\"web_app\":{\"url\":\"$APP_URL/yarashamiz.html\"}}}"
```
</details>

5. Mini App manzili: `$APP_URL/yarashamiz.html`

> GitHub Pages faqat statik HTML uchun ishlaydi — `api/` funksiyalari u yerda
> ishlamaydi, shuning uchun API alohida joyda (Vercel/Render) turishi kerak.

## Muammolarni hal qilish

### Botda Web App tugmasi chiqmayapti

Bu deyarli har doim quyidagi 3 sababdan biri:

| # | Sabab | Tekshirish | Yechim |
|---|---|---|---|
| 1 | **`APP_URL` o'rnatilmagan** | `/api/setup` javobida `"app"` bo'sh bo'lsa | `APP_URL` qo'shing. Telegram `https://` bo'lmagan URL ni qabul qilmaydi va xabar umuman yuborilmaydi |
| 2 | **Webhook o'rnatilmagan** | `getWebhookInfo` da `url` bo'sh | `/api/setup?key=...` ni chaqiring |
| 3 | **`WEBHOOK_SECRET` mos emas** | `getWebhookInfo` da `last_error_message: "401 Unauthorized"` | `WEBHOOK_SECRET` ni o'chiring yoki `setWebhook` da `secret_token` bilan bir xil qiymat bering |

Diagnostika:

```bash
# Webhook holati
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"

# Menyu tugmasi holati
curl "https://api.telegram.org/bot$BOT_TOKEN/getChatMenuButton"
```

Vercel > Deployments > Functions > Logs bo'limida `[telegram]` bilan
boshlanadigan qatorlarni qidiring — kod endi barcha Telegram xatolarini
shu yerda yozadi.

## Lokal ishlab chiqish

```bash
npm install
npx vercel dev
```

`?api=` parametrisiz ochilsa, frontend ichidagi `MOCK` ma'lumotlar bilan
ishlaydi (server kerak emas).
