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
  marmar: 'Marmar 🤍',
  night: 'Tun 🌙', gold: 'Oltin ⭐', ocean: 'Okean 🌊', royal: 'Shohona 👑',
  aurora: "Shimol yog'dusi 🌌", blossom: 'Gulzor 🌸', velvet: 'Baxmal 🍷', sky: 'Osmon ☁️',
};

/* 3D konvert + ichidagi qog'oz (xat) */
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
  paper.appendChild(h('p', 'pl-text', L.t || L.text || "(bo'sh xat)"));
  el.appendChild(paper);
  env.appendChild(el);
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

  /* --- matn --- */
  const c1 = h('div', 'card');
  c1.appendChild(h('h2', '', '✍️ Xat yozish'));
  c1.appendChild(h('p', '', f.isPrem ? '💎 Cheksiz xat'
    : ('Bugun qoldi: ' + f.left + ' / ' + f.limit)));
  const ta = document.createElement('textarea');
  ta.placeholder = "Uzr so'rang, samimiy bo'ling…";
  ta.maxLength = f.textMax;
  ta.style.cssText = 'width:100%;min-height:120px;margin-top:10px;border-radius:14px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff3f7;padding:12px;font:400 15px Nunito;resize:none';
  c1.appendChild(ta);
  const cnt = h('p', 'hint', '0 / ' + f.textMax);
  ta.oninput = () => { cnt.textContent = ta.value.length + ' / ' + f.textMax; };
  c1.appendChild(cnt);
  v.appendChild(c1);

  /* --- takliflar --- */
  const c2 = h('div', 'card');
  c2.appendChild(h('h2', '', '🎁 Uchrashuv taklifi'));
  c2.appendChild(h('p', '', "Bir nechtasini tanlang (yoki o'zingiznikini yozing)"));
  const grid = h('div', 'tgrid');
  c2.appendChild(grid);
  function renderOffers() {
    grid.innerHTML = '';
    f.offers.concat(S.offers.filter((o) => f.offers.indexOf(o) < 0)).forEach((o) => {
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

  const ownRow = h('div');
  ownRow.style.cssText = 'display:flex;gap:8px;margin-top:10px';
  const inp = document.createElement('input');
  inp.placeholder = "O'z taklifingiz (40 belgi)";
  inp.maxLength = 40;
  inp.style.cssText = 'flex:1;min-height:44px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff3f7;padding:0 12px;font:400 14px Nunito';
  ownRow.appendChild(inp);
  const add = h('button', 'btn btn-ghost btn-sm', '+');
  add.style.minWidth = '54px';
  add.onclick = () => {
    haptic();
    const t = inp.value.trim();
    if (!t) return;
    if (!f.isPrem && S.custom.length >= 1) {
      return alert("Bepul versiyada 1 ta o'z taklifi. Premium — cheksiz 💎");
    }
    if (S.offers.indexOf(t) > -1) return;
    S.offers.push(t); S.custom.push(t);
    inp.value = '';
    renderOffers();
  };
  ownRow.appendChild(add);
  c2.appendChild(ownRow);
  v.appendChild(c2);

  /* --- dizayn --- */
  const c3 = h('div', 'card');
  c3.appendChild(h('h2', '', '🎨 Dizayn'));
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
    b.dataset.theme = t.id;
    tgrid.appendChild(b);
  });
  c3.appendChild(tgrid);
  v.appendChild(c3);

  /* --- yaratish --- */
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
    if (!r.ok) {
      return alert(r.err === 'limit' ? 'Bugungi limit tugadi (' + f.limit + ')'
        : r.err === 'premium' ? 'Bu dizayn Premium uchun 💎'
        : r.err === 'offers' ? 'Kamida bitta taklif tanlang'
        : 'Xatolik yuz berdi');
    }
    confetti();
    ta.value = ''; cnt.textContent = '0 / ' + f.textMax;
    S.offers = []; S.custom = []; renderOffers();
    out.style.display = 'flex';
    out.style.flexDirection = 'column';
    out.style.gap = '10px';
    out.innerHTML = '';
    const card = letterCard(r.id, text, S.offers.length ? S.offers : [], S.theme);
    out.appendChild(card);
    const linkBox = h('div', 'card');
    linkBox.appendChild(h('h2', '', '🔗 Havola tayyor'));
    const lk = h('p', '', r.link);
    lk.style.cssText = 'word-break:break-all;font-size:12.5px;opacity:.85';
    linkBox.appendChild(lk);
    const copy = h('button', 'btn btn-ghost', '📋 Nusxalash');
    copy.style.marginTop = '10px';
    copy.onclick = () => { navigator.clipboard.writeText(r.link); alert('Nusxalandi ✅'); };
    linkBox.appendChild(copy);
    const sh = h('button', 'btn btn-main', '📤 Telegramda yuborish');
    sh.onclick = () => {
      const u = 'https://t.me/share/url?url=' + encodeURIComponent(r.link) + '&text=' + encodeURIComponent('Senga xat bor 💌');
      if (tg && tg.openTelegramLink) tg.openTelegramLink(u); else window.open(u);
    };
    linkBox.appendChild(sh);
    out.appendChild(linkBox);
    out.scrollIntoView({ behavior: 'smooth' });
  };
}

function letterCard(id, text, offers, theme) {
  const c = h('div', 'card theme-' + (theme || 'classic'));
  c.appendChild(h('h2', '', '👁 Sizning xatingiz'));
  c.appendChild(h('p', 'letter-text', text));
  if (offers && offers.length) {
    const off = h('div', 'offers');
    offers.forEach((o) => off.appendChild(h('span', '', '💝 ' + o)));
    c.appendChild(off);
  }
  return c;
}

/* --- xatni rasm (PNG) qilib saqlash --- */
const CARD_COLORS = {
  classic: ['#2a0f3d', '#12061c'], love: ['#5a1030', '#2a0716'],
  sunset: ['#5a2a10', '#1f0d06'], mint: ['#0f3d2e', '#06140f'],
  marmar: ['#f6f9ff', '#c9d7ef'],
  night: ['#101a3d', '#060814'], gold: ['#4a3a10', '#171105'],
  ocean: ['#0a2a4a', '#04101c'], royal: ['#3a1050', '#140620'],
  aurora: ['#103a3a', '#061414'], blossom: ['#4a1030', '#1a0612'],
  velvet: ['#3a0a1a', '#14040a'], sky: ['#1a2a4a', '#080d18'],
};
// och fonli dizaynlarda matn rangi
const CARD_INK = { marmar: '#243044' };

function wrapLines(ctx, text, maxW) {
  const words = [];
  String(text || '').split(/\s+/).forEach((w) => {
    let chunk = '';
    for (const ch of w) {
      if (chunk && ctx.measureText(chunk + ch).width > maxW) {
        words.push(chunk); chunk = ch;
      } else chunk += ch;
    }
    if (chunk) words.push(chunk);
  });
  const lines = [];
  let line = '';
  words.forEach((w) => {
    const t = line ? line + ' ' + w : w;
    if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; }
    else line = t;
  });
  if (line) lines.push(line);
  return lines;
}

function saveCard(v, text, theme) {
  const W = 720, H = 960;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  if (!ctx) return;
  const c = CARD_COLORS[theme] || CARD_COLORS.classic;
  const ink = CARD_INK[theme] || '#fff3f7';
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, c[0]); g.addColorStop(1, c[1]);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = theme === 'marmar' ? 'rgba(36,48,68,.18)' : 'rgba(255,255,255,.22)';
  ctx.lineWidth = 2;
  ctx.strokeRect(30, 30, W - 60, H - 60);
  ctx.textAlign = 'center';
  ctx.fillStyle = ink;
  ctx.font = '700 36px Nunito, sans-serif';
  ctx.fillText('💌 Yarashamiz', W / 2, 120);
  ctx.font = '400 30px Nunito, sans-serif';
  const all = wrapLines(ctx, text, W - 150);
  const lines = all.slice(0, 14);
  if (all.length > 14) {
    lines[13] = lines[13].replace(/\s+\S*$/, '') + '…';
  }
  let y = 250;
  lines.forEach((ln) => { ctx.fillText(ln, W / 2, y); y += 46; });
  ctx.font = '400 22px Nunito, sans-serif';
  ctx.fillStyle = theme === 'marmar' ? 'rgba(36,48,68,.6)' : 'rgba(255,243,247,.65)';
  ctx.fillText('t.me — Yarashamiz ❤️', W / 2, H - 70);

  let url;
  try {
    url = cv.toDataURL('image/png');
  } catch (e) {
    alert('Rasm yaratilmadi, qayta urinib ko‘ring');
    return;
  }

  const card = h('div', 'card');
  card.appendChild(h('h2', '', '🖼 Rasm tayyor'));
  const img = h('img');
  img.src = url;
  img.style.cssText = 'width:100%;border-radius:14px;margin-top:8px';
  card.appendChild(img);
  card.appendChild(h('p', 'hint', 'Rasmni uzoq bosib «Saqlash»ni tanlang'));
  const a = h('a', 'btn btn-ghost', '⬇️ Yuklab olish');
  a.href = img.src; a.download = 'yarashamiz-xat.png';
  a.style.cssText = 'display:block;text-align:center;text-decoration:none;margin-top:10px';
  card.appendChild(a);
  v.appendChild(card);
  card.scrollIntoView({ behavior: 'smooth' });
}

/* --- havola orqali kelgan xat (oluvchi) --- */
function letterOpen(v) {
  const menu = h('div');
  // `hidden` atributi inline display bilan bekor bo'lardi — shuning uchun
  // konvert ochilmaguncha display:none
  menu.style.cssText = 'display:none;flex-direction:column;gap:9px;margin-top:10px';

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

  /* --- javob yozish --- */
  const replyBtn = h('button', 'btn btn-ghost', '✍️ Javob yozish');
  replyBtn.onclick = () => {
    haptic();
    menu.style.display = 'none';           // xat oynasi yo'qolmasin
    const box = h('div');
    box.style.cssText = 'display:flex;flex-direction:column;gap:9px;margin-top:10px';
    const ta = document.createElement('textarea');
    ta.placeholder = 'Javobingizni yozing (300 belgigacha)...';
    ta.maxLength = 300;
    ta.style.cssText = 'width:100%;min-height:100px;border-radius:14px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.08);color:#fff3f7;padding:12px;font:400 15px Nunito;resize:none';
    box.appendChild(ta);
    const send = h('button', 'btn btn-main', 'Yuborish');
    send.onclick = () => {
      const t = ta.value.trim();
      if (!t) return;
      haptic('medium');
      sendReply(t);
    };
    box.appendChild(send);
    const back = h('button', 'btn btn-ghost', 'Orqaga');
    back.onclick = () => { haptic(); box.remove(); menu.style.display = 'flex'; };
    box.appendChild(back);
    v.appendChild(box);
    ta.focus();
  };
  menu.appendChild(replyBtn);

  const saveBtn = h('button', 'btn btn-ghost', '🖼 Rasm qilib saqlash');
  saveBtn.onclick = () => { haptic(); saveCard(v, LETTER.t, LETTER.theme); };
  menu.appendChild(saveBtn);

  const rep = h('button', 'btn btn-ghost', '⚠️ Shikoyat qilish');
  rep.style.color = '#ffb36b';
  rep.onclick = () => {
    if (confirm('Shikoyat qilinsinmi? Yuboruvchidan boshqa xat kelmaydi va admin xabardor bo‘ladi.')) {
      haptic('heavy');
      sendAnswer('report', sel);
    }
  };
  menu.appendChild(rep);

  mountScene(v, { t: LETTER.t, theme: LETTER.theme }, {
    after: 'Sizni o\'ylayotgan odam bor ❤️',
    onOpen: () => { menu.style.display = 'flex'; },
  });
  v.appendChild(menu);
}

function sendAnswer(a, o) {
  if (!LETTER_ID) return tg.close();
  tg.sendData(JSON.stringify({ a, l: LETTER_ID, o: o || '' }));
  tg.close();
}

function sendReply(txt) {
  if (!LETTER_ID) return tg.close();
  tg.sendData(JSON.stringify({ a: 'reply', l: LETTER_ID, t: txt }));
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
    pr.appendChild(h('p', '', 'Cheksiz xat · AI yordamchi · 8 shablon · Sevgi kvizi'));
    const pz = h('div', 'price');
    const pm = h('div'); pm.appendChild(h('b', '', ME.prices.month + ' ⭐')); pm.appendChild(h('small', '', '1 oy'));
    const py = h('div'); py.appendChild(h('b', '', ME.prices.year + ' ⭐')); py.appendChild(h('small', '', '1 yil + 2 oy'));
    const pg = h('div'); pg.appendChild(h('b', '', ME.prices.gift + ' ⭐')); pg.appendChild(h('small', '', 'sovg\'a'));
    pz.appendChild(pm); pz.appendChild(py); pz.appendChild(pg);
    pr.appendChild(pz);
    pr.appendChild(h('p', 'hint', 'Sotib olish uchun botdagi 💎 Premium tugmasini bosing'));
  }
  v.appendChild(pr);

  /* --- taklif / eslatmalar --- */
  const rf = h('div', 'card');
  rf.appendChild(h('h2', '', '🎁 Do‘stlarni taklif qilish'));
  rf.appendChild(h('p', '', 'Har bir taklif: +10 ball · 3 ta — 7 kun premium, 10 ta — 30 kun'));
  rf.appendChild(h('p', 'hint',
    'Bosganlar: ' + (ME.refs || 0) + ' · Birinchi xat yozganlar: ' + (ME.refsOk || 0)));
  if (ME.invite) {
    const lk = h('p', 'hint', ME.invite);
    lk.style.cssText = 'word-break:break-all;font-size:12px';
    rf.appendChild(lk);
    const cp = h('button', 'btn btn-ghost', '📋 Havolani nusxalash');
    cp.onclick = () => { navigator.clipboard.writeText(ME.invite); alert('Nusxalandi ✅'); };
    rf.appendChild(cp);
    const sh = h('button', 'btn btn-main', '📤 Do‘stga yuborish');
    sh.style.marginTop = '8px';
    sh.onclick = () => {
      const u = 'https://t.me/share/url?url=' + encodeURIComponent(ME.invite)
        + '&text=' + encodeURIComponent('Senga bir xat bor 💌');
      if (tg && tg.openTelegramLink) tg.openTelegramLink(u); else window.open(u);
    };
    rf.appendChild(sh);
  } else {
    rf.appendChild(h('p', 'hint',
      'Havola hozircha mavjud emas (BOT_USERNAME sozlanmagan). Botda /invite dan foydalaning.'));
  }
  const rm = h('button', 'btn btn-ghost',
    ME.remind ? '🔕 Eslatmalarni o‘chirish' : '🔔 Eslatmalarni yoqish');
  rm.style.marginTop = '8px';
  rm.onclick = async () => {
    haptic();
    const r = await api('remind', { on: !ME.remind });
    if (r && r.ok) {
      ME.remind = r.remind;
      rm.textContent = ME.remind ? '🔕 Eslatmalarni o‘chirish' : '🔔 Eslatmalarni yoqish';
    }
  };
  rf.appendChild(rm);
  v.appendChild(rf);

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
  if (LETTER) {
    const nav = document.querySelector('.tabs');
    if (nav) nav.style.display = 'none';
    letterOpen($('view'));
    return;
  }
  const r = await api('me');
  if (r.ok) { ME = r; $('pill').textContent = (r.pts || 0) + ' ball'; }
  setTab('write');
})();
