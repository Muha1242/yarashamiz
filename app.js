/* Yarashamiz Mini App — xatni ochish va javob berish */
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.BackButton.hide();

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const letterId = params.get('l') || '';

/* URL-safe base64 ni oddiy base64 ga aylantiramiz */
function decodePayload(d) {
  try {
    return JSON.parse(atob(d.replace(/-/g, '+').replace(/_/g, '/')));
  } catch (e) { return { t: '', o: [], theme: 'classic' }; }
}

const letter = decodePayload(params.get('d') || '');
const THEME_NAMES = { classic: 'Klassik', love: 'Sevgi ❤️', night: 'Tun 🌙', gold: 'Oltin ⭐' };

/* --- render --- */
$('card').className = 'card theme-' + (letter.theme || 'classic');
$('letter').textContent = letter.t || '(bo\'sh xat)';
$('theme-badge').textContent = THEME_NAMES[letter.theme] || 'Klassik';
$('offers').innerHTML = (letter.o || []).map(o => `<span>💝 ${o}</span>`).join('');

let selected = (letter.o || [])[0] || '';
if (letter.o && letter.o.length > 1) {
  $('offer-list').innerHTML = letter.o.map((o, i) =>
    `<button data-i="${i}" class="${i === 0 ? 'sel' : ''}">${o}</button>`).join('');
  $('offer-list').querySelectorAll('button').forEach(b =>
    b.onclick = () => {
      $('offer-list').querySelectorAll('button').forEach(x => x.classList.remove('sel'));
      b.classList.add('sel');
      selected = letter.o[+b.dataset.i];
      haptic('light');
    });
} else {
  $('menu-title').textContent = 'Uchrashuv taklifi qabul qilinsinmi?';
}

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
  setTimeout(() => send('yes'), 900);
};
$('btn-heart').onclick = () => { haptic('light'); send('heart'); };
$('btn-later').onclick = () => { haptic('light'); send('later'); };
$('btn-stop').onclick = () => {
  if (confirm('Bu odam sizga boshqa xat yozmasligi kerakmi?')) send('stop');
};

function haptic(s) { try { tg.HapticFeedback.impactOccurred(s); } catch (e) {} }

/* --- konfetti --- */
function confetti() {
  const cv = $('confetti'), ctx = cv.getContext('2d');
  cv.width = innerWidth; cv.height = innerHeight;
  const colors = ['#E91E63', '#9C27B0', '#FFD700', '#fff', '#4CAF50'];
  const parts = Array.from({ length: 90 }, () => ({
    x: innerWidth / 2 + (Math.random() - .5) * 140,
    y: innerHeight / 3,
    vx: (Math.random() - .5) * 9,
    vy: Math.random() * -9 - 3,
    s: Math.random() * 7 + 4,
    c: colors[Math.random() * colors.length | 0],
    r: Math.random() * Math.PI,
  }));
  (function frame() {
    ctx.clearRect(0, 0, cv.width, cv.height);
    let alive = false;
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += .25; p.r += .1;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * .6);
      ctx.restore();
      if (p.y < cv.height + 40) alive = true;
    }
    if (alive) requestAnimationFrame(frame);
    else ctx.clearRect(0, 0, cv.width, cv.height);
  })();
}

/* --- fon yuraklari --- */
(function hearts() {
  const box = document.querySelector('.hearts');
  for (let i = 0; i < 12; i++) {
    const s = document.createElement('span');
    s.textContent = '❤️';
    s.style.left = Math.random() * 100 + 'vw';
    s.style.fontSize = (14 + Math.random() * 22) + 'px';
    s.style.animationDuration = (7 + Math.random() * 9) + 's';
    s.style.animationDelay = (-Math.random() * 10) + 's';
    box.appendChild(s);
  }
})();

$('menu').hidden = false;
