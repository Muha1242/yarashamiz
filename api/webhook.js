const { send, openKb } = require("../lib/core");
module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(200).send("ok");
  const m = (req.body || {}).message;
  if (m && m.text && m.text.startsWith("/start")) {
    const a = m.text.split(" ")[1] || "";
    const l = /^l_\d+$/.test(a) ? a.slice(2) : null;
    await send(m.chat.id, l ? "Sizga xat bor" : "Yarashamiz. Arazni chiroyli tugating.", openKb(l));
  }
  res.status(200).send("ok");
};
