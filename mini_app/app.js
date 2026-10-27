/* ===== Yarashamiz Mini App — v3.2 To'liq Versiya ===== */
const tg = window.Telegram.WebApp;
tg.ready(); tg.expand(); tg.BackButton.hide();
try { tg.setHeaderColor('#2a0f3d'); tg.setBackgroundColor('#12061c'); } catch (e) {}

const $ = (id) => document.getElementById(id);
const P = new URLSearchParams(location.search);
const API_BASE = P.get('api') || location.origin;
const LETTER_ID = P.get('l') || '';

function decodePayload(d) {
  try { return JSON.parse(atob(d.replace(/-/g, '+').replace(/_/g, '/'))); }
  catch (e) { return null; }
}
const LETTER = decodePayload(P.get('d') || '');

async function api(action, extra) {
  try {
    const r = await fetch(API_BASE + '/api/app', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ init: tg.initData, action }, extra || {})),
    });
    return await r.json();
  } catch (e) { return { ok: false, err: 'net' }; }
}

const h = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const haptic = (s) => { try { tg.HapticFeedback.impactOccurred(s || 'light'); } catch (e) {} };

function setTab(name) {
  document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === name));
  const v = $('view'); v.innerHTML = '';
  window.scrollTo(0, 0);
  ({ write: viewWrite, capsules: viewCapsules, coupons: viewCoupons }[name] || viewWrite)(v);
}
document.querySelectorAll('.tabs button').forEach((b) => (b.onclick = () => { haptic(); setTab(b.dataset.tab); }));

function viewWrite(v) {
  const c = h('div', 'card');
  c.appendChild(h('h2', '', '✍️ Xat yozish'));
  c.appendChild(h('p', '', 'Mini App orqali xat yozing va yuboring'));
  v.appendChild(c);
}

async function viewCapsules(v) {
  v.innerHTML = '<div class="card"><h2>⏳ Vaqt Kapsulasi</h2><p>Kelajakdagi maxsus sanaga yoziladigan xatlar (Premium)</p></div>';
}

async function viewCoupons(v) {
  v.innerHTML = '<div class="card"><h2>🎟️ Sevgi Biletlari</h2><p>Juftingizga vaucherlar yuboring</p></div>';
}

(async function start() {
  if (LETTER) { return; }
  setTab('write');
})();
