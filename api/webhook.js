const { send, openKb, APP } = require("../lib/core");

// Telegram webhook maxfiy tokeni. O'rnatilsa (tavsiya etiladi), har bir so'rovda
// X-Telegram-Bot-Api-Secret-Token sarlavhasi tekshiriladi va begona POST rad etiladi.
// DIQQAT: agar WEBHOOK_SECRET o'rnatilgan bo'lsa, setWebhook'da ham xuddi shu
// qiymat `secret_token` sifatida berilishi SHART, aks holda Telegram so'rovlari
// 401 bilan rad etiladi va bot umuman javob bermaydi.
const SECRET = process.env.WEBHOOK_SECRET || "";

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(200).send("ok");
  if (SECRET && req.headers["x-telegram-bot-api-secret-token"] !== SECRET) return res.status(401).send("unauthorized");
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
    const m = body.message;
    if (m && m.text && m.text.startsWith("/start")) {
      if (!APP) {
        // Web App tugmasi "https://" bilan boshlanishi shart. APP_URL bo'lmasa
        // Telegram BUTTON_URL_INVALID beradi va xabar umuman yuborilmaydi.
        await send(m.chat.id, "Sozlash tugallanmagan: APP_URL o'rnatilmagan. Vercel > Settings > Environment Variables bo'limida APP_URL qo'shing (masalan https://loyiha.vercel.app), keyin /api/setup?key=... ni chaqiring.");
        return res.status(200).send("ok");
      }
      const a = m.text.split(" ")[1] || "";
      const l = /^l_\d+$/.test(a) ? a.slice(2) : null;
      await send(m.chat.id, l ? "Sizga xat bor" : "Yarashamiz. Arazni chiroyli tugating.", openKb(l));
    }
  } catch (e) { console.error(e); }
  res.status(200).send("ok");
};
