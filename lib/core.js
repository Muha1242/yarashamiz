const crypto = require("crypto");
const { Redis } = require("@upstash/redis");

const TOKEN = process.env.BOT_TOKEN || "";
const APP = (process.env.APP_URL || "").replace(/\/$/, "");
const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN,
});
const DAILY_LIMIT = 3, PREMIUM_NEED = 100;
const MISSIONS = ["Bugun juftingizga 3 ta yaxshi gap ayting.", "Juftingizning sevimli qo'shig'ini qo'yib bering.",
  "Birga o'tgan eng yaxshi kunni eslab yozing.", "Kichik syurpriz qiling: choy yoki shirinlik.",
  "Juftingizdan bugun nima yordam kerakligini so'rang.", "Birga rasmga tushing.", "Juftingizga ovozli xabar yuboring."];
const G = ["ab", "wh", "ms", "ll", "lm"];
const ACTIONS = ["yes", "later", "stop", "report"];
const NAMES = { ab: "A yoki B", wh: "Kim ko'proq?", ms: "Kunlik missiya", ll: "Sevgi tili testi", lm: "Sirli savollar" };
const day = () => new Date(Date.now() + 5 * 36e5).toISOString().slice(0, 10);
const dayNum = () => Math.floor((Date.now() + 5 * 36e5) / 864e5);
const top = (d) => { let b = 0, bc = -1; for (let k = 0; k < 5; k++) { const c = d.filter((x) => x === k).length; if (c > bc) { bc = c; b = k; } } return b; };

function auth(init) {
  try {
    const p = new URLSearchParams(init); const hash = p.get("hash"); if (!hash) return null; p.delete("hash");
    const s = [...p.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([k, v]) => `${k}=${v}`).join("\n");
    const key = crypto.createHmac("sha256", "WebAppData").update(TOKEN).digest();
    const h = crypto.createHmac("sha256", key).update(s).digest("hex");
    if (h.length !== hash.length || !crypto.timingSafeEqual(Buffer.from(h), Buffer.from(hash))) return null;
    if (Date.now() / 1000 - Number(p.get("auth_date") || 0) > 86400 * 3) return null;
    return JSON.parse(p.get("user"));
  } catch (e) { return null; }
}

async function tg(method, body) {
  try {
    const r = await fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return await r.json();
  } catch (e) { return { ok: false }; }
}
let uname;
async function botName() { if (!uname) { const r = await tg("getMe", {}); uname = r.result && r.result.username; } return uname; }
const send = (chat, text, kb) => tg("sendMessage", { chat_id: chat, text, reply_markup: kb });
const openKb = (l) => ({ inline_keyboard: [[{ text: "Yarashamiz'ni ochish", web_app: { url: `${APP}/yarashamiz.html?api=${encodeURIComponent(APP)}${l ? `&l=${l}` : ""}` } }]] });

async function pairOf(u) {
  const id = await redis.get(`up:${u}`); if (!id) return null;
  const p = await redis.get(`pair:${id}`); if (!p) return null;
  return { id, a: Number(p.a), b: Number(p.b), since: p.since || null };
}
const other = (p, u) => (p.a === u ? p.b : p.a);
const ansKey = (pid, g, u) => `ans:${pid}:${day()}:${g}:${u}`;
const getAns = (pid, g, u) => redis.get(ansKey(pid, g, u));
const putAns = (pid, g, u, d) => redis.set(ansKey(pid, g, u), d, { ex: 172800 });

async function me(u, b, usr) {
  if (usr && usr.first_name) await redis.set(`ini:${u}`, String(usr.first_name)[0].toUpperCase());
  const p = await pairOf(u);
  const used = Number(await redis.get(`lim:${u}:${day()}`)) || 0;
  const prem = Number(await redis.get("prem:count")) || Number(process.env.PREMIUM_COUNT) || 0;
  const out = { left: Math.max(0, DAILY_LIMIT - used), prem, need: PREMIUM_NEED, bot: await botName(), pair: !!p, mission: MISSIONS[dayNum() % MISSIONS.length] };
  if (p) {
    const o = other(p, u); out.games = {}; out.res = {};
    for (const g of G) {
      const [mine, theirs] = await Promise.all([getAns(p.id, g, u), getAns(p.id, g, o)]);
      out.games[g] = { me: mine != null, him: theirs != null };
      if (mine != null && theirs != null) {
        // wh: javoblarni ko'ruvchiga nisbatan 1=siz, 0=juftingiz ga keltiramiz
        out.res[g] = g === "wh" ? { mine: mine.map((x) => (x === u ? 1 : 0)), him: theirs.map((x) => (x === u ? 1 : 0)) } : { mine, him: theirs };
      }
    }
    out.pts = Number(await redis.get(`pts:${p.id}`)) || 0;
    const [mi, hi, cm, ch, st, ids] = await Promise.all([redis.get(`ini:${u}`), redis.get(`ini:${o}`), redis.get(`ci:${p.id}:${day()}:${u}`), redis.get(`ci:${p.id}:${day()}:${o}`), redis.get(`streak:${p.id}`), redis.lrange(`caps:${p.id}`, 0, -1)]);
    out.ini = { me: mi || "?", him: hi || "?" }; out.since = p.since;
    out.ci = { me: cm, him: cm != null && ch != null ? ch : null, himDone: ch != null };
    out.streak = st && (st.last === day() || st.last === yday()) ? st.c : 0;
    out.caps = [];
    for (const id of ids || []) {
      const c = await redis.get(`cap:${id}`); if (!c) continue;
      const ready = c.open <= Date.now();
      out.caps.push({ id, open: c.open, mine: c.sender === u, ready, text: ready ? c.text : undefined });
    }
  }
  return out;
}

async function letterNew(u, b) {
  const text = String(b.text || "").trim().slice(0, 450);
  const offers = (Array.isArray(b.offers) ? b.offers : []).map((x) => String(x).slice(0, 40)).slice(0, 6);
  if (!text || !offers.length) return { err: "empty" };
  if ((Number(await redis.get(`rep:${u}`)) || 0) >= 3) return { err: "banned" };
  const key = `lim:${u}:${day()}`; const used = Number(await redis.get(key)) || 0;
  if (used >= DAILY_LIMIT) return { err: "limit" };
  await redis.incr(key); await redis.expire(key, 172800);
  const id = await redis.incr("letters:seq");
  await redis.set(`letter:${id}`, { sender: u, text, offers, th: Math.abs(parseInt(b.theme) || 0) % 3, ts: Date.now() }, { ex: 2592000 });
  return { link: `https://t.me/${await botName()}?start=l_${id}` };
}
const getLetter = (l) => (/^\d+$/.test(String(l)) ? redis.get(`letter:${l}`) : null);

async function letterGet(u, b) {
  const L = await getLetter(b.l); if (!L) return { err: "none" };
  if (await redis.sismember(`blk:${u}`, L.sender)) return { err: "blocked" };
  return { text: L.text, offers: L.offers, th: L.th || 0, mine: L.sender === u };
}

async function respond(u, b) {
  const L = await getLetter(b.l); if (!L || L.sender === u) return { err: "none" };
  const s = L.sender, a = b.a;
  if (!ACTIONS.includes(a)) return { err: "bad" };
  const rk = `resp:${b.l}:${u}`;
  if (a !== "later" && (await redis.get(rk)) != null) return { ok: 1 };
  if (a === "stop" || a === "report") {
    await redis.sadd(`blk:${u}`, s);
    if (a === "report") await redis.incr(`rep:${s}`);
  } else if (a === "yes") {
    const pu = await pairOf(u);
    const already = pu && (pu.a === s || pu.b === s);
    if (!already) {
      const ps = await pairOf(s);
      if (pu || ps) {
        await send(s, "Javob: yarashamiz. Hozir yangi juftlik ochilmadi, chunki akkauntlardan biri boshqa juftlikda.");
      } else {
        const id = await redis.incr("pairs:seq");
        await redis.set(`pair:${id}`, { a: s, b: u, since: day() }); await redis.set(`up:${s}`, id); await redis.set(`up:${u}`, id);
        await send(s, `Javob: yarashamiz. Taklif: ${String(b.o || "").slice(0, 40)}\nEndi birga o'ynashingiz mumkin.`, openKb());
      }
    } else {
      await send(s, `Javob: yarashamiz. Taklif: ${String(b.o || "").slice(0, 40)}\nEndi birga o'ynashingiz mumkin.`, openKb());
    }
  } else await send(s, "Javob: hali tayyor emas, keyinroq.");
  if (a !== "later") await redis.set(rk, 1, { ex: 2592000 });
  return { ok: 1 };
}

function valid(g, d) {
  if (!Array.isArray(d)) return g === "ms";
  if (g === "ab") return d.length === 5 && d.every((x) => Array.isArray(x) && x.length === 2 && x.every((v) => v === 0 || v === 1));
  if (g === "wh") return d.length === 5 && d.every((v) => v === 0 || v === 1);
  if (g === "ll") return d.length === 5 && d.every((v) => Number.isInteger(v) && v >= 0 && v <= 4);
  if (g === "lm") return d.length === 3 && d.every((v) => typeof v === "string" && v.trim());
  return false;
}

async function play(u, b) {
  const g = b.g; let d = b.data; const p = await pairOf(u);
  if (!G.includes(g) || !p || !valid(g, d) || (await getAns(p.id, g, u)) != null) return { err: "bad" };
  const o = other(p, u);
  if (g === "wh") d = d.map((x) => (x === 0 ? u : o));
  if (g === "ms") d = { ok: 1 };
  if (g === "lm") d = d.map((x) => x.trim().slice(0, 140));
  await putAns(p.id, g, u, d);
  const od = await getAns(p.id, g, o);
  if (od == null) { await send(o, `Juftingiz «${NAMES[g]}» o'yinini o'ynadi. Siz ham o'ynang.`, openKb()); return { ok: 1, pts: null }; }
  let pts = 0;
  if (g === "ab") for (let i = 0; i < 5; i++) pts += 2 * (d[i][1] === od[i][0]) + 2 * (od[i][1] === d[i][0]) + (d[i][0] === od[i][0]);
  else if (g === "wh") pts = 2 * d.filter((x, i) => x === od[i]).length;
  else if (g === "ll") pts = 10 + 5 * (top(d) === top(od) ? 1 : 0);
  else pts = 10;
  await redis.incrby(`pts:${p.id}`, pts);
  await send(o, `«${NAMES[g]}» natijasi: ${pts} ball. Ikkalangiz ham qatnashdingiz.`, openKb());
  return { ok: 1, pts };
}

const yday = () => new Date(Date.now() + 5 * 36e5 - 864e5).toISOString().slice(0, 10);

async function checkin(u, b) {
  const mood = b.mood; const p = await pairOf(u);
  if (!p || ![0, 1, 2, 3].includes(mood)) return { err: "bad" };
  const key = `ci:${p.id}:${day()}:${u}`;
  if ((await redis.get(key)) != null) return { err: "bad" };
  await redis.set(key, mood, { ex: 172800 });
  const o = other(p, u); const om = await redis.get(`ci:${p.id}:${day()}:${o}`);
  if (om == null) { await send(o, "Juftingiz bugungi kayfiyatini belgiladi. Siz ham belgilang.", openKb()); return { ok: 1, both: false }; }
  const st = (await redis.get(`streak:${p.id}`)) || { c: 0, last: "" };
  const c = st.last === day() ? st.c : st.last === yday() ? st.c + 1 : 1;
  await redis.set(`streak:${p.id}`, { c, last: day() });
  await redis.incrby(`pts:${p.id}`, 5);
  await send(o, `Check-in tayyor. Ketma-ket kunlar: ${c}. +5 ball.`, openKb());
  return { ok: 1, both: true, streak: c };
}

async function capsuleNew(u, b) {
  const p = await pairOf(u); const text = String(b.text || "").trim().slice(0, 400);
  const days = [7, 30, 365].includes(b.days) ? b.days : 0;
  if (!p || !text || !days) return { err: "bad" };
  const key = `capn:${u}:${day()}`; if ((Number(await redis.get(key)) || 0) >= 2) return { err: "limit" };
  await redis.incr(key); await redis.expire(key, 172800);
  const id = await redis.incr("caps:seq");
  await redis.set(`cap:${id}`, { sender: u, text, open: Date.now() + days * 864e5 }, { ex: (days + 30) * 86400 });
  await redis.rpush(`caps:${p.id}`, id);
  await send(other(p, u), `Juftingiz sizga vaqt kapsulasi qoldirdi. U ${days} kundan keyin ochiladi.`, openKb());
  return { ok: 1 };
}

const wrap = (fn) => async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "POST,OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const b = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
    const usr = auth(b.init || ""); if (!usr || !usr.id) return res.status(401).json({ err: "auth" });
    res.status(200).json(await fn(usr.id, b, usr));
  } catch (e) { console.error(e); res.status(500).json({ err: "server" }); }
};
module.exports = { wrap, checkin, capsuleNew, me, letterNew, letterGet, respond, play, send, openKb };
