const { tg, appBase } = require("../lib/core");

// Bir marta bosish bilan sozlash: webhook + chat menyu tugmasi.
//
// Ishlatish:  https://<domen>/api/setup          (SETUP_KEY bo'lmasa)
//             https://<domen>/api/setup?key=...  (SETUP_KEY bo'lsa)
//
// Xavfsizlik: bu endpoint HECH QANDAY parametr qabul qilmaydi — u faqat
// shu loyihaning o'z domenini webhook va menyu tugmasi qilib o'rnatadi.
// Ya'ni begona odam chaqirsa ham faqat TO'G'RI sozlamani o'rnatadi, zarar
// yetkaza olmaydi. Baribir qulflamoqchi bo'lsangiz — SETUP_KEY env qo'ying,
// shunda kalitsiz so'rovlar rad etiladi.
module.exports = async (req, res) => {
  const key = process.env.SETUP_KEY || "";
  const given = String((req.query && req.query.key) || "");
  if (key && given !== key) return res.status(403).json({ err: "forbidden" });

  if (!process.env.BOT_TOKEN) return res.status(400).json({ err: "no_bot_token", hint: "Vercel'da BOT_TOKEN env o'rnating" });

  const app = appBase();
  if (!app) return res.status(400).json({ err: "no_app_url", hint: "APP_URL env o'rnating yoki VERCEL_URL mavjud bo'lsin" });

  // Hozirgi holat (diagnostika uchun foydali)
  const before = await tg("getWebhookInfo", {});

  const secret = process.env.WEBHOOK_SECRET || "";
  const webhookBody = { url: `${app}/api/webhook`, allowed_updates: ["message"] };
  if (secret) webhookBody.secret_token = secret;

  const webhook = await tg("setWebhook", webhookBody);
  const menu = await tg("setChatMenuButton", {
    menu_button: { type: "web_app", text: "Yarashamiz", web_app: { url: `${app}/yarashamiz.html` } },
  });
  const me = await tg("getMe", {});

  res.status(200).json({
    app,
    bot: me && me.result && me.result.username,
    before: before && before.result,
    webhook,
    menu,
    ok: !!(webhook && webhook.ok) && !!(menu && menu.ok),
  });
};
