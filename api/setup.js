const { tg, appBase } = require("../lib/core");

// Bir marta bosish bilan sozlash: webhook + chat menyu tugmasi.
//
// Ishlatish:  https://<domen>/api/setup?key=<SETUP_KEY>
//
// Xavfsizlik: SETUP_KEY env o'rnatilmagan bo'lsa endpoint butunlay o'chirilgan.
module.exports = async (req, res) => {
  const key = process.env.SETUP_KEY || "";
  const given = String((req.query && req.query.key) || "");
  if (!key) return res.status(403).json({ err: "setup_off", hint: "Vercel'da SETUP_KEY env o'rnating, keyin /api/setup?key=<qiymat> bilan chaqiring" });
  if (given !== key) return res.status(403).json({ err: "forbidden" });

  const app = appBase();
  if (!app) return res.status(400).json({ err: "no_app_url", hint: "APP_URL env o'rnating (masalan https://loyiha.vercel.app)" });
  if (!process.env.BOT_TOKEN) return res.status(400).json({ err: "no_bot_token", hint: "BOT_TOKEN env o'rnating" });

  const secret = process.env.WEBHOOK_SECRET || "";
  const webhookBody = { url: `${app}/api/webhook`, allowed_updates: ["message"] };
  if (secret) webhookBody.secret_token = secret;

  const webhook = await tg("setWebhook", webhookBody);
  const menu = await tg("setChatMenuButton", {
    menu_button: { type: "web_app", text: "Yarashamiz", web_app: { url: `${app}/yarashamiz.html` } },
  });
  const info = await tg("getWebhookInfo", {});
  const me = await tg("getMe", {});

  res.status(200).json({
    app,
    bot: me && me.result && me.result.username,
    webhook,
    menu,
    info: info && info.result,
    ok: !!(webhook && webhook.ok) && !!(menu && menu.ok),
  });
};
