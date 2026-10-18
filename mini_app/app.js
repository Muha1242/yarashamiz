/* ===== Yarashamiz Mini App — 3D konvert va javoblar ===== */
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.BackButton.hide();
try { tg.setHeaderColor('#2a0f3d'); tg.setBackgroundColor('#12061c'); } catch (e) {}

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const letterId = params.get('l') || '';

/* URL-safe base64 -> oddiy base64 */
function decodePayload(d) {
  try {
    return JSON.parse(atob(d.replace(/-/g, '+').replace(/_/g, '/')));
  } catch (e) { return { t: '', o: [], theme: 'classic' }; }
}
const letter = decodePayload(params.get('d') || '');

/* Eski (v2) havolalar ?api=... ko'rinishida bo'lgan - ularda xat matni yo'q */
const IS_OLD_LINK = !params.get('d') && !!params.get('api');
const THEME_NAMES = { classic: 'Klassik', love: 'Sevgi ❤️', night: 'Tun 🌙', gold: 'Oltin ⭐' };

/* --- xatni tayyorlash (konvert ochilgach ko'rinadi) --- */
$('card').className = 'card theme-' + (letter.theme || 'classic');
$('letter').textContent = letter.t || "(bo'sh xat)";
$('theme-badge').textContent = THEME_NAMES[letter.theme] || 'Klassik';
$('offers').innerHTML = (letter.o || []).map((o) => `<span>💝 ${o}</span>`).join('');

if (IS_OLD_LINK) {
  document.querySelector('.brand').textContent = '⏳ Havola eskirgan';
  $('letter').textContent = `Bu havola eski versiyadan qolgan.

Iltimos, botga qaytib, yangi xat so'rang ❤️`;
  $('theme-badge').textContent = '';
}

let selected = (letter.o || [])[0] || '';
if (letter.o && letter.o.length > 1) {
  $('offer-list').innerHTML = letter.o.map((o, i) =>
    `<button data-i="${i}" class="${i === 0 ? 'sel' : ''}">${o}</button>`).join('');
  $('offer-list').querySelectorAll('button').forEach((b) => {
    b.onclick = () => {
      $('offer-list').querySelectorAll('button').forEach((x) => x.classList.remove('sel'));
      b.classList.add('sel');
      selected = letter.o[+b.dataset.i];
      haptic('light');
    };
  });
} else {
  $('menu-title').textContent = 'Uchrashuv taklifi qabul qilinsinmi?';
}

/* ===== 3D konvertni ochish ===== */
let opened = false;
function openEnvelope() {
  if (opened) return;
  opened = true;
  haptic('medium');
  $('scene').classList.add('open');
  $('hint').style.opacity = '0';
  sparkle($('scene'));
  setTimeout(() => {
    $('hint').textContent = 'Sizni o\'ylayotgan odam bor ❤️';
    $('hint').style.opacity = '.75';
  }, 1000);
  setTimeout(() => {
    $('card').hidden = false;
    $('menu').hidden = false;
    haptic('light');
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }, 1150);
}
if (IS_OLD_LINK) {
  $('envelope').onclick = () => { $('card').hidden = false; haptic('light'); };
  $('hint').textContent = "Botga qaytib, yangi xat so'rang";
} else {
  $('envelope').onclick = openEnvelope;
}
if (!IS_OLD_LINK) $('scene').onclick = openEnvelope;

/* --- javoblar --- */
function send(a, extra = {}) {
  if (!letterId) return tg.close();
  tg.sendData(JSON.stringify({ a, l: letterId, o: selected, ...extra }));
  tg.close();
}

$('btn-yes').onclick = () => {
  haptic('heavy');
  confetti();
  $('btn-yes').textContent = '❤️ Yarashamiz!';
  $('btn-yes').style.transform = 'scale(1.06)';
  setTimeout(() => send('yes'), 950);
};
$('btn-heart').onclick = () => { haptic('light'); burstHearts(); setTimeout(() => send('heart'), 500); };
$('btn-later').onclick = () => { haptic('light'); send('later'); };
$('btn-stop').onclick = () => {
  if (confirm('Bu odam sizga boshqa xat yozmasligi kerakmi?')) send('stop');
};

function haptic(s) { try { tg.HapticFeedback.impactOccurred(s); } catch (e) {} }

/* ===== konfetti (3D aylanadi) ===== */
function confetti() {
  const cv = $('confetti');
  const ctx = cv.getContext ? cv.getContext('2d') : null;
  if (!ctx) return;                       // canvas yo'q bo'lsa - jim o'tadi
  const dpr = window.devicePixelRatio || 1;
  cv.width = innerWidth * dpr; cv.height = innerHeight * dpr;
  ctx.scale(dpr, dpr);
  const colors = ['#E91E63', '#9C27B0', '#FFD700', '#ffffff', '#4CAF50', '#ff7aa8'];
  const parts = Array.from({ length: 130 }, () => ({
    x: innerWidth / 2 + (Math.random() - .5) * 180,
    y: innerHeight / 3,
    vx: (Math.random() - .5) * 11,
    vy: Math.random() * -13 - 4,
    s: Math.random() * 9 + 4,
    c: colors[(Math.random() * colors.length) | 0],
    r: Math.random() * Math.PI,
    vr: (Math.random() - .5) * .35,
    sq: Math.random() * .7 + .25,      // 3D taqlid: kenglik siqilishi
    sp: Math.random() * .07 + .02,
  }));
  (function frame() {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    let alive = false;
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += .28; p.vx *= .995; p.r += p.vr;
      const w = p.s * Math.abs(Math.cos(p.sp += .06));   // yon tomonga aylanayotgandek
      ctx.save();
      ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.c;
      ctx.fillRect(-w / 2, -p.s * p.sq / 2, w, p.s * p.sq);
      ctx.restore();
      if (p.y < innerHeight + 60) alive = true;
    }
    if (alive) requestAnimationFrame(frame);
    else ctx.clearRect(0, 0, innerWidth, innerHeight);
  })();
}

/* ===== konvert atrofida uchqunlar ===== */
function sparkle(box) {
  const r = box.getBoundingClientRect();
  for (let i = 0; i < 18; i++) {
    const s = document.createElement('span');
    s.className = 'spark';
    s.textContent = ['✨', '💫', '⭐'][(Math.random() * 3) | 0];
    s.style.cssText = `position:fixed;left:${r.left + Math.random() * r.width}px;` +
      `top:${r.top + Math.random() * r.height}px;font-size:${10 + Math.random() * 16}px;` +
      `pointer-events:none;z-index:8;transition:transform 1.2s ease-out,opacity 1.2s;`;
    document.body.appendChild(s);
    requestAnimationFrame(() => {
      s.style.transform = `translate(${(Math.random() - .5) * 190}px,${-70 - Math.random() * 120}px) rotate(${Math.random() * 320}deg) scale(.3)`;
      s.style.opacity = '0';
    });
    setTimeout(() => s.remove(), 1300);
  }
}

/* ===== yurak yomg'iri ===== */
function burstHearts() {
  for (let i = 0; i < 14; i++) {
    const s = document.createElement('span');
    s.textContent = ['❤️', '💖', '💝'][(Math.random() * 3) | 0];
    s.style.cssText = `position:fixed;left:${innerWidth / 2}px;top:${innerHeight / 2}px;` +
      `font-size:${16 + Math.random() * 22}px;pointer-events:none;z-index:10;` +
      `transition:transform 1.1s cubic-bezier(.2,.8,.2,1),opacity 1.1s;`;
    document.body.appendChild(s);
    requestAnimationFrame(() => {
      s.style.transform = `translate(${(Math.random() - .5) * 300}px,${-120 - Math.random() * 260}px) rotate(${(Math.random() - .5) * 90}deg)`;
      s.style.opacity = '0';
    });
    setTimeout(() => s.remove(), 1200);
  }
}

/* ===== fon yuraklari ===== */
(function hearts() {
  const box = document.querySelector('.hearts');
  for (let i = 0; i < 14; i++) {
    const s = document.createElement('span');
    s.textContent = ['❤️', '💗', '💜'][(Math.random() * 3) | 0];
    s.style.left = Math.random() * 100 + 'vw';
    s.style.fontSize = (12 + Math.random() * 24) + 'px';
    s.style.animationDuration = (9 + Math.random() * 11) + 's';
    s.style.animationDelay = (-Math.random() * 12) + 's';
    box.appendChild(s);
  }
})();

/* konvert ochilmaguncha xat yashirin */
$('card').hidden = true;
$('menu').hidden = true;
