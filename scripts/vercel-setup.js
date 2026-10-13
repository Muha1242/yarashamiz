// Vercel build vaqtida webhook va chat menyu tugmasini AVTOMATIK o'rnatadi.
//
// Natijada foydalanuvchi hech narsa qo'lda sozlashi shart emas — faqat
// BOT_TOKEN env bo'lishi kifoya. Har deployda qayta ishga tushadi.
//
// Xavfsizlik/qulaylik:
//  - faqat VERCEL_ENV === "production" bo'lganda ishlaydi
//    (aks holda preview deploylar production webhook'ini o'g'irlab ketardi)
//  - xato bo'lsa deploy TO'XTATILMAYDI (hech qachon exit 1 qilmaydi)

const TOKEN = process.env.BOT_TOKEN || "";
const ENV = process.env.VERCEL_ENV || "";
const RAW_APP = process.env.APP_URL || process.env.VERCEL_PROJECT_PRODUCTION_URL || "";

function withProto(a) {
  const v = String(a || "").trim().replace(/\/+$/, "");
  if (!v) return "";
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

async function call(method, body) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 10000);
  try {
    const r = await fetch(`https://api.telegram.org/bot${TOKEN}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    return await r.json();
  } finally {
    clearTimeout(timer);
  }
}

(async () => {
  if (!TOKEN) return console.log("[setup] BOT_TOKEN yo'q — o'tkazib yuborildi");
  if (ENV !== "production") return console.log(`[setup] VERCEL_ENV=${ENV || "yo'q"} — faqat production deployda ishlaydi`);

  const app = withProto(RAW_APP);
  if (!app) return console.log("[setup] APP_URL aniqlanmadi — /api/setup?key=... ni qo'lda chaqiring");

  const secret = process.env.WEBHOOK_SECRET || "";
  const webhookBody = { url: `${app}/api/webhook`, allowed_updates: ["message"] };
  if (secret) webhookBody.secret_token = secret;

  const w = await call("setWebhook", webhookBody);
  console.log("[setup] setWebhook:", w && w.ok ? "OK" : `XATO — ${(w && w.description) || "javob yo'q"}`);

  const m = await call("setChatMenuButton", {
    menu_button: { type: "web_app", text: "Yarashamiz", web_app: { url: `${app}/yarashamiz.html` } },
  });
  console.log("[setup] setChatMenuButton:", m && m.ok ? "OK" : `XATO — ${(m && m.description) || "javob yo'q"}`);

  console.log(`[setup] tayyor. app=${app}`);
})().catch((e) => console.log("[setup] kutilmagan xato (deploy davom etadi):", e.message));
