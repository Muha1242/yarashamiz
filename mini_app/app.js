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
  ({ letter: viewLetter, games: viewGames, me: viewMe, memory: viewMemory, garden: viewGarden }[name] || viewMe)(v);
}
document.querySelectorAll('.tabs button').forEach((b) => (b.onclick = () => { haptic(); setTab(b.dataset.tab); }));

/* ================= 1. XAT ================= */
const THEME_NAMES = {
  classic: 'Klassik', love: 'Sevgi ❤️', sunset: 'Quyosh 🌅', mint: 'Yalpiz 🍃',
  night: 'Tun 🌙', gold: 'Oltin ⭐', ocean: 'Okean 🌊', royal: 'Shohona 👑',
};

function letterBody(card, txt, offers, theme) {
  card.className = 'card theme-' + (theme || 'classic');
  card.appendChild(h('p', 'letter-text', txt || "(bo'sh xat)"));
  if (offers && offers.length) {
    const off = h('div', 'offers');
    offers.forEach((o) => off.appendChild(h('span', '', '💝 ' + o)));
    card.appendChild(off);
  }
  card.appendChild(h('p', 'hint', THEME_NAMES[theme] || 'Klassik'));
  return card;
}

function viewLetter(v) {
  if (LETTER) return letterOpen(v);
  return letterPreview(v);
}

/* --- o'zi yozgan xatni ko'rish + dizayn o'zgartirish --- */
async function letterPreview(v) {
  v.appendChild(h('div', 'splash', 'Yuklanmoqda…'));
  const r = await api('letter');
  v.innerHTML = '';
  if (!r.ok) {
    const c = h('div', 'card');
    c.appendChild(h('h2', '', '💌 Xat'));
    c.appendChild(h('p', '', "Hali xat yozmadingiz.\n\nBotda «✍️ Xat yozish» ni bosing"));
    v.appendChild(c);
    return;
  }
  v.appendChild(h('p', 'hint', r.mine ? '👁 Sizning xatingiz — shunday ko\'rinadi' : '💌 Sizga kelgan xat'));
  v.appendChild(letterBody(h('div'), r.text, r.offers, r.theme));

  if (!r.mine) return;
  const pick = h('div', 'card');
  pick.appendChild(h('h2', '', '🎨 Dizayn'));
  pick.appendChild(h('p', '', 'O\'zgartirish imkoniyati: ' + r.changesLeft + ' / 3'));
  const grid = h('div', 'tgrid');
  r.themes.forEach((t) => {
    const b = h('button', 'tbtn' + (t.id === r.theme ? ' on' : '') + (t.ok ? '' : ' lock'), t.name);
    b.onclick = async () => {
      haptic();
      if (!t.ok) return alert('Bu dizayn Premium uchun 💎');
      if (r.changesLeft <= 0) return alert("O'zgartirish limiti tugadi (3/3)");
      const res = await api('retheme', { l: r.id, theme: t.id });
      if (!res.ok) return alert(res.err === 'limit' ? 'Limit tugadi (3/3)' : 'Xatolik yuz berdi');
      haptic('medium');
      LETTER_ID_CACHE = r.id;
      setTab('letter');
    };
    grid.appendChild(b);
  });
  pick.appendChild(grid);
  v.appendChild(pick);
}

let LETTER_ID_CACHE = '';

/* --- havola orqali ochilgan xat (3D konvert) --- */
function letterOpen(v) {
  const scene = h('div', 'scene');
  const heart = h('div', 'heart3d');
  heart.appendChild(h('div', 'h-half h-left'));
  heart.appendChild(h('div', 'h-half h-right'));
  heart.appendChild(h('div', 'h-glow'));
  scene.appendChild(heart);

  const env = h('div', 'envelope');
  env.appendChild(h('div', 'env-back'));
  const el = h('div', 'env-letter');
  const paper = h('div', 'pl-inner theme-' + (LETTER.theme || 'classic'));
  paper.appendChild(h('p', 'pl-text', LETTER.t || ''));
  el.appendChild(paper);
  env.appendChild(el);
  env.appendChild(h('div', 'env-front'));
  env.appendChild(h('div', 'env-flap'));
  scene.appendChild(env);
  v.appendChild(scene);
  const hint = h('p', 'hint', '✨ Konvertni bosing');
  v.appendChild(hint);

  const card = h('div', 'card'); card.hidden = true;
  card.style.padding = '12px 16px';
  if (LETTER.o && LETTER.o.length) {
    const off = h('div', 'offers');
    LETTER.o.forEach((o) => off.appendChild(h('span', '', '💝 ' + o)));
    card.appendChild(off);
  } else { card.style.display = 'none'; }
  v.appendChild(card);

  const menu = h('div'); menu.hidden = true;
  menu.style.cssText = 'display:flex;flex-direction:column;gap:9px;margin-top:4px';
  let sel = (LETTER.o || [])[0] || '';
  if (LETTER.o && LETTER.o.length > 1) {
    const opt = h('div', 'opt');
    LETTER.o.forEach((o, i) => {
      const b = h('button', i === 0 ? 'sel' : '', o);
      b.onclick = () => { haptic(); opt.querySelectorAll('button').forEach((x) => x.classList.remove('sel')); b.classList.add('sel'); sel = o; };
      opt.appendChild(b);
    });
    menu.appendChild(opt);
  }
  const yes = h('button', 'btn btn-main', '❤️ Yarashamiz');
  yes.onclick = () => { haptic('heavy'); confetti(); yes.textContent = '❤️ Yarashamiz!'; setTimeout(() => sendAnswer('yes', sel), 900); };
  menu.appendChild(yes);
  const later = h('button', 'btn btn-ghost', '⏳ Keyinroq');
  later.onclick = () => sendAnswer('later', sel);
  menu.appendChild(later);
  const stop = h('button', 'btn btn-ghost', '🚫 Boshqa xat olmayman');
  stop.style.color = '#ff9a9a';
  stop.onclick = () => { if (confirm('Bu odam sizga boshqa xat yozmasinmi?')) sendAnswer('stop', sel); };
  menu.appendChild(stop);
  v.appendChild(menu);

  env.onclick = () => {
    if (scene.classList.contains('open')) return;
    haptic('medium'); scene.classList.add('open'); hint.textContent = '';
    setTimeout(() => { card.hidden = false; menu.hidden = false; haptic('light'); }, 900);
  };
}

function sendAnswer(a, o) {
  if (!LETTER_ID) return tg.close();
  tg.sendData(JSON.stringify({ a, l: LETTER_ID, o: o || '' }));
  tg.close();
}

/* ================= 2. O'YINLAR ================= */
let GAMES_CACHE = null;
async function viewGames(v) {
  v.appendChild(h('div', 'splash', 'Yuklanmoqda…'));
  const r = await api('games');
  v.innerHTML = '';
  if (!r.ok) { v.appendChild(h('p', 'hint', "Xatolik: " + (r.err || '?') + "\nIlovani botdan oching")); return; }
  if (!r.pair) {
    const c = h('div', 'card');
    c.appendChild(h('h2', '', '🎮 O\'yinlar'));
    c.appendChild(h('p', '', "O'yinlar juftingiz bilan yarashgandan keyin ochiladi."));
    v.appendChild(c); return;
  }
  GAMES_CACHE = r.games;
  const head = h('div', 'card');
  head.appendChild(h('h2', '', '🎮 Bugungi o\'yinlar'));
  head.appendChild(h('p', '', 'Ball faqat ikkalangiz ham o\'ynasangiz beriladi.'));
  v.appendChild(head);
  r.games.forEach((g) => {
    const el = h('div', 'game' + (g.locked ? ' locked' : ''));
    const left = h('div');
    left.appendChild(h('b', '', g.name + (g.prem ? ' 💎' : '')));
    left.appendChild(h('small', '', g.mode === 'guess' ? "O'zingiz + juftingizni toping"
      : g.mode === 'mission' ? 'Kichik vazifa' : g.mode === 'talk' ? 'Erkin javob'
      : g.opt ? g.opt.join(' / ') : 'Savol-javob'));
    el.appendChild(left);
    const right = h('div'); right.style.textAlign = 'right';
    const b1 = h('span', 'badge' + (g.done ? ' ok' : ''), g.done ? '✅ siz' : '⏳ siz');
    const b2 = h('span', 'badge' + (g.him ? ' ok' : ''), g.him ? '✅ juft' : '⏳ juft');
    b2.style.marginLeft = '6px';
    right.appendChild(b1); right.appendChild(b2);
    el.appendChild(right);
    el.onclick = () => {
      haptic();
      if (g.locked) return alert('Bu o\'yin Premium uchun 💎');
      if (g.done) return alert('Bugun o\'ynadingiz ✅');
      playGame(v, g);
    };
    v.appendChild(el);
  });
}

function playGame(v, g) {
  v.innerHTML = '';
  const bar = h('div', 'qbar'); const fill = h('b'); fill.style.width = '0%'; bar.appendChild(fill);
  v.appendChild(bar);
  const q = h('div', 'qtext'); v.appendChild(q);
  const box = h('div', 'qopt'); v.appendChild(box);

  if (g.mode === 'mission') {
    q.textContent = g.qs[0];
    const b = h('button', 'btn btn-main', '✅ Bajardim');
    b.onclick = () => submit(g, {});
    v.appendChild(b); return;
  }
  if (g.mode === 'talk') {
    q.textContent = g.qs[0];
    const ta = document.createElement('textarea');
    ta.placeholder = 'Javobingizni yozing…';
    ta.style.cssText = 'width:100%;min-height:110px;border-radius:14px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff3f7;padding:12px;font:400 15px Nunito;resize:none';
    ta.maxLength = 250; v.appendChild(ta);
    const b = h('button', 'btn btn-main', 'Yuborish'); b.style.marginTop = '10px';
    b.onclick = () => { if (!ta.value.trim()) return; submit(g, [ta.value.trim()]); };
    v.appendChild(b); return;
  }

  /* guess (ab) yoki match (wh, qz) */
  const ans = [];
  let step = 0, own = null;
  const total = g.n * (g.mode === 'guess' ? 2 : 1);
  function render() {
    fill.style.width = Math.round((step / total) * 100) + '%';
    box.innerHTML = '';
    const idx = Math.floor(step / (g.mode === 'guess' ? 2 : 1));
    const qq = g.qs[idx];
    const opts = g.mode === 'guess' ? [qq[1], qq[2]] : g.opt;
    q.textContent = (idx + 1) + '/' + g.n + '. ' + (g.mode === 'guess' ? qq[0] : qq);
    opts.forEach((o, i) => {
      const b = h('button', '', o);
      b.onclick = () => {
        haptic();
        if (g.mode === 'guess') {
          if (own === null) { own = i; render(); }
          else { ans.push([own, i]); own = null; step++; next(); }
        } else { ans.push(i); step++; next(); }
      };
      box.appendChild(b);
    });
    if (g.mode === 'guess' && own !== null) q.textContent += ' → juftingiz? ';
  }
  function next() { if (step >= total) submit(g, ans); else render(); }
  render();
}

async function submit(g, data) {
  const v = $('view');
  v.innerHTML = ''; v.appendChild(h('div', 'splash', 'Yuborilmoqda…'));
  const r = await api('answer', { g: g.id, data });
  v.innerHTML = '';
  const c = h('div', 'card');
  if (!r.ok) {
    c.appendChild(h('h2', '', 'Xatolik'));
    c.appendChild(h('p', '', r.err === 'already' ? "Bugun o'ynadingiz ✅"
      : r.err === 'premium' ? 'Bu o\'yin Premium uchun 💎' : 'Qayta urinib ko\'ring'));
  } else if (r.waiting) {
    c.appendChild(h('h2', '', '✅ Qabul qilindi'));
    c.appendChild(h('p', '', 'Juftingiz ham o\'ynagach ball qo\'shiladi.'));
  } else {
    confetti();
    c.appendChild(h('h2', '', '🎯 Natija'));
    c.appendChild(h('p', '', 'Ikkalangiz ham o\'ynadingiz!'));
    const g2 = h('div', 'stat-grid');
    const a = h('div', 'stat'); a.appendChild(h('b', '', '+' + (r.result ? r.result.pts : 0))); a.appendChild(h('small', '', 'ball'));
    g2.appendChild(a);
    const b = h('div', 'stat'); b.appendChild(h('b', '', (r.result ? r.result.streak : 0))); b.appendChild(h('small', '', 'kun ketma-ket'));
    g2.appendChild(b);
    c.appendChild(g2);
  }
  const back = h('button', 'btn btn-ghost', 'Orqaga'); back.style.marginTop = '14px';
  back.onclick = () => setTab('games');
  v.appendChild(c); v.appendChild(back);
}

/* ================= 3. HISOBIM ================= */
async function viewMe(v) {
  if (!ME) { v.appendChild(h('div', 'splash', 'Yuklanmoqda…')); const r = await api('me'); if (!r.ok) { v.innerHTML = ''; v.appendChild(h('p', 'hint', 'Ilovani botdan oching')); return; } ME = r; }
  v.innerHTML = '';
  if (ME.pts != null) $('pill').textContent = ME.pts + ' ball';

  const hi = h('div', 'card');
  hi.appendChild(h('h2', '', 'Salom, ' + (ME.user.name || "Do'st")));
  hi.appendChild(h('p', '', ME.pair ? 'Juftingiz bilan ulangansiz ❤️' : 'Hali juft ulanmagansiz'));
  v.appendChild(hi);

  const gr = h('div', 'stat-grid');
  const s = (val, lab) => { const d = h('div', 'stat'); d.appendChild(h('b', '', val)); d.appendChild(h('small', '', lab)); return d; };
  gr.appendChild(s(ME.streak || 0, 'kun ketma-ket'));
  gr.appendChild(s(ME.pts || 0, 'juftlik bali'));
  gr.appendChild(s(ME.days || 0, 'birga kunlar'));
  gr.appendChild(s(ME.letters || 0, 'xatlar'));
  v.appendChild(gr);

  const pr = h('div', 'card');
  pr.appendChild(h('h2', '', '💎 Premium'));
  if (ME.prem) pr.appendChild(h('p', '', 'Faol — ' + ME.premDays + ' kun qoldi'));
  else {
    pr.appendChild(h('p', '', 'Cheksiz xat · AI yordamchi · 4 shablon · Sevgi kvizi'));
    const pz = h('div', 'price');
    const pm = h('div'); pm.appendChild(h('b', '', ME.prices.month + ' ⭐')); pm.appendChild(h('small', '', '1 oy'));
    const py = h('div'); py.appendChild(h('b', '', ME.prices.year + ' ⭐')); py.appendChild(h('small', '', '1 yil + 2 oy'));
    const pg = h('div'); pg.appendChild(h('b', '', ME.prices.gift + ' ⭐')); pg.appendChild(h('small', '', 'sovg\'a'));
    pz.appendChild(pm); pz.appendChild(py); pz.appendChild(pg);
    pr.appendChild(pz);
    pr.appendChild(h('p', 'hint', 'Sotib olish uchun botdagi 💎 Premium tugmasini bosing'));
  }
  v.appendChild(pr);

  const tip = h('div', 'card');
  tip.appendChild(h('h2', '', '💡 Bugungi savol'));
  tip.appendChild(h('p', '', ME.mission || '—'));
  const ansBtn = h('button', 'btn btn-main', '✍️ Javob berish');
  ansBtn.style.marginTop = '12px';
  ansBtn.onclick = async () => {
    haptic();
    const r = await api('games');
    if (!r.ok || !r.pair) return alert('Avval juftingiz bilan yarashing ❤️');
    const kq = (r.games || []).find((x) => x.id === 'kq');
    if (!kq) return alert("O'yin topilmadi");
    if (kq.done) return alert('Bugun javob bergansiz ✅');
    document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b.dataset.tab === 'games'));
    playGame($('view'), kq);
  };
  tip.appendChild(ansBtn);
  v.appendChild(tip);
}

/* ================= 4. XOTIRALAR ================= */
async function viewMemory(v) {
  v.appendChild(h('div', 'splash', 'Yuklanmoqda…'));
  const r = await api('library');
  v.innerHTML = '';
  if (!r.ok) { v.appendChild(h('p', 'hint', 'Ilovani botdan oching')); return; }
  if (!r.letters.length) {
    const c = h('div', 'card');
    c.appendChild(h('h2', '', '📖 Xotiralar'));
    c.appendChild(h('p', '', "Hali xat yo'q. Birinchi xatni yozing!"));
    v.appendChild(c); return;
  }
  r.letters.forEach((x) => {
    const d = h('div', 'mem');
    d.appendChild(h('div', 't', '«' + x.text.slice(0, 120) + (x.text.length > 120 ? '…' : '') + '»'));
    const dt = new Date(x.ts * 1000).toLocaleDateString('uz');
    d.appendChild(h('div', 'm', (x.mine ? 'siz →' : '→ siz') + ' · ' + dt + ' · ' + (THEME_NAMES[x.theme] || 'Klassik')));
    v.appendChild(d);
  });
}

/* ================= 5. BOG'IM ================= */
const STAGES = [
  { min: 0, icon: '🌱', name: "Urug'" }, { min: 20, icon: '🌿', name: 'Nihol' },
  { min: 50, icon: '🌳', name: 'Yosh daraxt' }, { min: 100, icon: '🌸', name: 'Gullagan daraxt' },
  { min: 200, icon: '🍎', name: 'Mevali daraxt' }, { min: 350, icon: '✨', name: "Afsonaviy bog'" },
];
async function viewGarden(v) {
  if (!ME) { const r = await api('me'); if (r.ok) ME = r; }
  v.innerHTML = '';
  const pts = (ME && ME.pts) || 0;
  let i = 0; STAGES.forEach((s, k) => { if (pts >= s.min) i = k; });
  const cur = STAGES[i], nx = STAGES[i + 1];

  v.appendChild(h('div', 'gplant', cur.icon));
  const t = h('div', 'card');
  t.appendChild(h('h2', '', cur.name));
  t.appendChild(h('p', '', nx ? (nx.min - pts) + ' ball qolgach ' + nx.icon + ' ' + nx.name + " bo'ladi" : 'Eng yuqori bosqichga yetdingiz!'));
  const bar = h('div', 'qbar'); const f = h('b');
  f.style.width = (nx ? Math.round(((pts - cur.min) / (nx.min - cur.min)) * 100) : 100) + '%';
  bar.appendChild(f); bar.style.marginTop = '12px'; t.appendChild(bar);
  v.appendChild(t);

  const grid = h('div', 'ggrid');
  const st = (ME && ME.streak) || 0;
  for (let d = 0; d < 28; d++) grid.appendChild(h('div', 'gday' + (d >= 28 - st ? ' on' : ''), d >= 28 - st ? '🌸' : '·'));
  const g = h('div', 'card'); g.appendChild(h('h2', '', 'Gulzorimiz')); g.appendChild(grid);
  g.appendChild(h('p', 'hint', 'Har kuni botga kirib o\'ynang — gul o\'sadi'));
  v.appendChild(g);
}

/* ================= konfetti ================= */
function confetti() {
  const cv = $('confetti'); const ctx = cv.getContext && cv.getContext('2d');
  if (!ctx) return;
  const dpr = window.devicePixelRatio || 1;
  cv.width = innerWidth * dpr; cv.height = innerHeight * dpr; ctx.scale(dpr, dpr);
  const cols = ['#E91E63', '#9C27B0', '#FFD700', '#fff', '#4CAF50', '#ff7aa8'];
  const ps = Array.from({ length: 110 }, () => ({
    x: innerWidth / 2 + (Math.random() - .5) * 160, y: innerHeight / 3,
    vx: (Math.random() - .5) * 10, vy: Math.random() * -12 - 3,
    s: Math.random() * 8 + 4, c: cols[(Math.random() * cols.length) | 0],
    r: Math.random() * Math.PI, vr: (Math.random() - .5) * .3, sp: Math.random() * .07,
  }));
  (function frame() {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    let alive = false;
    for (const p of ps) {
      p.x += p.vx; p.y += p.vy; p.vy += .27; p.vx *= .995; p.r += p.vr;
      const w = p.s * Math.abs(Math.cos(p.sp += .06));
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c;
      ctx.fillRect(-w / 2, -p.s / 2, w, p.s); ctx.restore();
      if (p.y < innerHeight + 60) alive = true;
    }
    if (alive) requestAnimationFrame(frame); else ctx.clearRect(0, 0, innerWidth, innerHeight);
  })();
}

/* fon yuraklari */
(function hearts() {
  const box = document.querySelector('.hearts');
  for (let i = 0; i < 12; i++) {
    const s = h('span', '', ['❤️', '💗', '💜'][(Math.random() * 3) | 0]);
    s.style.left = Math.random() * 100 + 'vw';
    s.style.fontSize = (12 + Math.random() * 22) + 'px';
    s.style.animationDuration = (9 + Math.random() * 10) + 's';
    s.style.animationDelay = (-Math.random() * 12) + 's';
    box.appendChild(s);
  }
})();

/* ================= START ================= */
(async function start() {
  if (LETTER) { setTab('letter'); return; }
  const r = await api('me');
  if (r.ok) { ME = r; $('pill').textContent = (r.pts || 0) + ' ball'; }
  setTab(r.ok ? 'me' : 'letter');
})();
