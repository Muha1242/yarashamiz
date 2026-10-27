/* ===== Yarashamiz Mini App — to'liq ilova ===== */
const tg = window.Telegram.WebApp;
tg.ready(); tg.expand(); tg.BackButton.hide();
try { tg.setHeaderColor('#2a0f3d'); tg.setBackgroundColor('#12061c'); } catch (e) {}

const $ = (id) => document.getElementById(id);
const P = new URLSearchParams(location.search);
const API_BASE = P.get('api') || location.origin;
const LETTER_ID = P.get('l') || '';

/* --- xat yuklamasi (havoladan) --- */
function decodePayload(d) {
  try { return JSON.parse(atob(d.replace(/-/g, '+').replace(/_/g, '/'))); }
  catch (e) { return null; }
}
const LETTER = decodePayload(P.get('d') || '');

let ME = null;

/* ================= API ================= */
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

/* ================= TABLAR ================= */
function setTab(name) {
  document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === name));
  const v = $('view'); v.innerHTML = '';
  window.scrollTo(0, 0);
  ({ write: viewWrite, games: viewGames, me: viewMe, memory: viewMemory, garden: viewGarden }[name] || viewWrite)(v);
}
document.querySelectorAll('.tabs button').forEach((b) => (b.onclick = () => { haptic(); setTab(b.dataset.tab); }));

/* ================= 1. XAT ================= */
const THEME_NAMES = {
  classic: 'Klassik', love: 'Sevgi ❤️', sunset: 'Quyosh 🌅', mint: 'Yalpiz 🍃',
  night: 'Tun 🌙', gold: 'Oltin ⭐', ocean: 'Okean 🌊', royal: 'Shohona 👑',
  aurora: "Shimol yog'dusi 🌌", blossom: 'Gulzor 🌸', velvet: 'Baxmal 🍷', sky: 'Osmon ☁️',
};

/* 3D konvert + ichidagi qog'oz (xat) va tanlangan fon */
function mountScene(v, L, opts) {
  opts = opts || {};
  const scene = h('div', 'scene');
  const heart = h('div', 'heart3d');
  heart.appendChild(h('div', 'h-half h-left'));
  heart.appendChild(h('div', 'h-half h-right'));
  heart.appendChild(h('div', 'h-glow'));
  scene.appendChild(heart);

  const env = h('div', 'envelope');
  env.appendChild(h('div', 'env-back'));
  
  const el = h('div', 'env-letter');
  const paper = h('div', 'pl-inner theme-' + (L.theme || 'classic'));
  
  const paperContent = h('div', 'pl-content');
  paperContent.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;height:100%;padding:10px;overflow-y:auto';
  
  paperContent.appendChild(h('p', 'pl-text', L.t || L.text || "(bo'sh xat)"));
  
  const offersList = L.offers || L.o;
  if (offersList && offersList.length) {
    const off = h('div', 'offers');
    off.style.cssText = 'margin-top:6px;transform:scale(0.85);transform-origin:center';
    offersList.forEach((o) => off.appendChild(h('span', '', '💝 ' + o)));
    paperContent.appendChild(off);
  }
  
  paper.appendChild(paperContent);
  el.appendChild(paper);
  env.appendChild(h('div', 'env-front'));
  env.appendChild(h('div', 'env-flap'));
  scene.appendChild(env);
  v.appendChild(scene);

  const hint = h('p', 'hint', opts.hint || '✨ Konvertni bosing');
  v.appendChild(hint);

  let done = false;
  const open = () => {
    if (done) return;
    done = true;
    haptic('medium');
    scene.classList.add('open');
    hint.textContent = opts.after || '';
    setTimeout(() => { haptic('light'); if (opts.onOpen) opts.onOpen(); }, 900);
  };
  env.onclick = open;
  scene.onclick = open;
  return scene;
}

function viewWrite(v) {
  v.innerHTML = '';
  v.appendChild(h('div', 'splash', 'Yuklanmoqda…'));
  api('form').then((f) => {
    v.innerHTML = '';
    if (!f.ok) {
      const c = h('div', 'card');
      c.appendChild(h('h2', '', '✍️ Xat yozish'));
      c.appendChild(h('p', '', 'Ilovani botdan oching'));
      v.appendChild(c); return;
    }
    buildForm(v, f);
  });
}

function buildForm(v, f) {
  const S = { offers: [], theme: 'classic', custom: [] };

  const c1 = h('div', 'card');
  c1.appendChild(h('h2', '', '✍️ Xat yozish'));
  c1.appendChild(h('p', '', f.isPrem ? '💎 Cheksiz xat' : ('Bugun qoldi: ' + f.left + ' / ' + f.limit)));
  const ta = document.createElement('textarea');
  ta.placeholder = "Uzr so'rang, samimiy bo'ling…";
  ta.maxLength = f.textMax;
  ta.style.cssText = 'width:100%;min-height:120px;margin-top:10px;border-radius:14px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff3f7;padding:12px;font:400 15px Nunito;resize:none';
  c1.appendChild(ta);
  const cnt = h('p', 'hint', '0 / ' + f.textMax);
  ta.oninput = () => { cnt.textContent = ta.value.length + ' / ' + f.textMax; };
  c1.appendChild(cnt);
  v.appendChild(c1);

  const c2 = h('div', 'card');
  c2.appendChild(h('h2', '', '🎁 Uchrashuv taklifi'));
  c2.appendChild(h('p', '', "Bir nechtasini tanlang"));
  const grid = h('div', 'tgrid');
  c2.appendChild(grid);
  function renderOffers() {
    grid.innerHTML = '';
    f.offers.forEach((o) => {
      const on = S.offers.indexOf(o) > -1;
      const b = h('button', 'tbtn' + (on ? ' on' : ''), o);
      b.onclick = () => {
        haptic();
        const i = S.offers.indexOf(o);
        if (i > -1) S.offers.splice(i, 1); else S.offers.push(o);
        renderOffers();
      };
      grid.appendChild(b);
    });
  }
  renderOffers();
  v.appendChild(c2);

  const c3 = h('div', 'card');
  c3.appendChild(h('h2', '', '🎨 3D Dizayn va Fon'));
  const tgrid = h('div', 'tgrid');
  f.themes.forEach((t) => {
    const b = h('button', 'tbtn' + (t.id === S.theme ? ' on' : '') + (t.ok ? '' : ' lock'), t.name);
    b.onclick = () => {
      haptic();
      if (!t.ok) return alert('Bu dizayn Premium uchun 💎');
      S.theme = t.id;
      tgrid.querySelectorAll('.tbtn').forEach((x) => x.classList.remove('on'));
      b.classList.add('on');
    };
    tgrid.appendChild(b);
  });
  c3.appendChild(tgrid);
  v.appendChild(c3);

  const mk = h('button', 'btn btn-main', '💌 Havola yaratish');
  mk.style.marginTop = '4px';
  v.appendChild(mk);
  const out = h('div'); out.style.display = 'none';
  v.appendChild(out);

  mk.onclick = async () => {
    const text = ta.value.trim();
    if (!text) return alert('Xat matnini yozing');
    if (!S.offers.length) return alert('Kamida bitta taklif tanlang');
    haptic('medium');
    mk.disabled = true;
    mk.textContent = 'Yaratilmoqda…';
    const r = await api('newletter', { text, offers: S.offers, theme: S.theme });
    mk.disabled = false;
    mk.textContent = '💌 Havola yaratish';
    if (!r.ok) return alert('Xatolik yuz berdi');
    
    confetti();
    out.style.display = 'flex';
    out.style.flexDirection = 'column';
    out.style.gap = '10px';
    out.innerHTML = '';

    mountScene(out, { text, offers: S.offers, theme: S.theme }, {
      hint: '✨ Ochish uchun bosing',
      after: 'Sizning xatingiz 💌'
    });

    const linkBox = h('div', 'card');
    linkBox.appendChild(h('h2', '', '🔗 Havola tayyor'));
    const lk = h('p', '', r.link);
    lk.style.cssText = 'word-break:break-all;font-size:12.5px;opacity:.85';
    linkBox.appendChild(lk);
    const copy = h('button', 'btn btn-ghost', '📋 Nusxalash');
    copy.style.marginTop = '10px';
    copy.onclick = () => { navigator.clipboard.writeText(r.link); alert('Nusxalandi ✅'); };
    linkBox.appendChild(copy);
    out.appendChild(linkBox);
    out.scrollIntoView({ behavior: 'smooth' });
  };
}

function letterOpen(v) {
  const menu = h('div');
  menu.hidden = true;
  menu.style.cssText = 'display:flex;flex-direction:column;gap:9px;margin-top:10px';

  let sel = (LETTER.o || [])[0] || '';
  const yes = h('button', 'btn btn-main', '❤️ Yarashamiz');
  yes.onclick = () => { haptic('heavy'); confetti(); setTimeout(() => sendAnswer('yes', sel), 900); };
  menu.appendChild(yes);

  mountScene(v, { t: LETTER.t, theme: LETTER.theme, o: LETTER.o }, {
    after: 'Sizni o\'ylayotgan odam bor ❤️',
    onOpen: () => { menu.hidden = false; },
  });
  v.appendChild(menu);
}

function sendAnswer(a, o) {
  if (!LETTER_ID) return tg.close();
  tg.sendData(JSON.stringify({ a, l: LETTER_ID, o: o || '' }));
  tg.close();
}

function viewGames(v) { v.innerHTML = '<div class="card"><h2>🎮 O\'yinlar</h2><p>Tez kunda...</p></div>'; }
function viewMe(v) { v.innerHTML = '<div class="card"><h2>📊 Hisobim</h2><p>Profil malumotlari</p></div>'; }
function viewMemory(v) { v.innerHTML = '<div class="card"><h2>📖 Xotiralar</h2><p>Saqlangan xatlar</p></div>'; }
function viewGarden(v) { v.innerHTML = '<div class="card"><h2>🌱 Bog\'im</h2><p>Sevgi bog\'i</p></div>'; }

function confetti() {
  const cv = $('confetti'); const ctx = cv.getContext && cv.getContext('2d');
  if (!ctx) return;
  const dpr = window.devicePixelRatio || 1;
  cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; ctx.scale(dpr, dpr);
  const cols = ['#E91E63', '#9C27B0', '#FFD700', '#fff', '#4CAF50'];
  const ps = Array.from({ length: 80 }, () => ({
    x: innerWidth / 2, y: innerHeight / 3,
    vx: (Math.random() - .5) * 8, vy: Math.random() * -10 - 2,
    s: Math.random() * 6 + 3, c: cols[(Math.random() * cols.length) | 0],
  }));
  (function frame() {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    let alive = false;
    for (const p of ps) {
      p.x += p.vx; p.y += p.vy; p.vy += .25;
      ctx.fillStyle = p.c; ctx.fillRect(p.x, p.y, p.s, p.s);
      if (p.y < innerHeight + 50) alive = true;
    }
    if (alive) requestAnimationFrame(frame);
  })();
}

(async function start() {
  if (LETTER) {
    const nav = document.querySelector('.tabs');
    if (nav) nav.style.display = 'none';
    letterOpen($('view'));
    return;
  }
  setTab('write');
})();
