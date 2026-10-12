const { send, openKb } = require("../lib/core");

// Telegram webhook maxfiy tokeni. O'rnatilsa (tavsiya etiladi), har bir so'rovda
// X-Telegram-Bot-Api-Secret-Token sarlavhasi tekshiriladi va begona POST rad etiladi.
const SECRET = process.env.WEBHOOK_SECRET || "";

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(200).send("ok");
  if (SECRET && req.headers["x-telegram-bot-api-secret-token"] !== SECRET) return res.status(401).send("unauthorized");
  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
    const m = body.message;
    if (m && m.text && m.text.startsWith("/start")) {
      const a = m.text.split(" ")[1] || "";
      const l = /^l_\d+$/.test(a) ? a.slice(2) : null;
      await send(m.chat.id, l ? "Sizga xat bor" : "Yarashamiz. Arazni chiroyli tugating.", openKb(l));
    }
  } catch (e) { console.error(e); }
  res.status(200).send("ok");
};
