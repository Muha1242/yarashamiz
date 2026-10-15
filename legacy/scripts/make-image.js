// /start uchun chiroyli rasm (public/start.png) yaratadi.
// Tashqi kutubxonasiz: PNG o'zi kodlanadi (zlib Node'da mavjud).
//
// Ishlatish:  node scripts/make-image.js

const zlib = require("zlib");
const fs = require("fs");
const path = require("path");

const W = 1200, H = 630;
const R = 200;                       // yurak radiusi
const cx = W / 2, cy = H / 2 + 6;

let TBL = null;
function crcTable() {
  if (TBL) return TBL;
  TBL = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    TBL[n] = c;
  }
  return TBL;
}
function crc32(buf) {
  const t = crcTable();
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = t[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([len, body, crc]);
}

// yurak egri chizig'i: f <= 0 -> ichida
function heartF(nx, ny) {
  const a = nx * nx + ny * ny - 1;
  return a * a * a - nx * nx * ny * ny * ny;
}
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v) => (v < 0 ? 0 : v > 255 ? 255 : v);

// uchqunlar
let seed = 987654321;
const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
const sparkles = [];
for (let i = 0; i < 26; i++) {
  sparkles.push({ x: rnd() * W, y: rnd() * H, r: 1.4 + rnd() * 3.2, a: 0.35 + rnd() * 0.6 });
}

const raw = Buffer.alloc((W * 3 + 1) * H);
let off = 0;
for (let py = 0; py < H; py++) {
  raw[off++] = 0; // filter: none
  for (let px = 0; px < W; px++) {
    // fon gradienti
    const dx = (px - cx) / (W * 0.62), dy = (py - cy) / (H * 0.62);
    const d = Math.min(1, Math.sqrt(dx * dx + dy * dy));
    let r = lerp(0x5a, 0x12, d), g = lerp(0x22, 0x06, d), b = lerp(0x74, 0x1c, d);

    // yurak qoplamasi (3x3 supersampling -> silliq qirra)
    let cov = 0;
    for (let sy = 0; sy < 3; sy++) {
      for (let sx = 0; sx < 3; sx++) {
        const nx = (px + (sx + 0.5) / 3 - cx) / R;
        const ny = -((py + (sy + 0.5) / 3) - cy) / R;
        if (heartF(nx, ny) <= 0) cov++;
      }
    }
    cov /= 9;

    // atrofidagi yumshoq porlash
    const nx0 = (px - cx) / R, ny0 = -(py - cy) / R;
    const f0 = heartF(nx0, ny0);
    if (f0 > 0) {
      const glow = Math.exp(-f0 * 1.5) * 0.5;
      r = r + (255 - r) * glow * 0.8;
      g = g + (150 - g) * glow * 0.6;
      b = b + (205 - b) * glow * 0.75;
    }

    // yurak ichi: pushti -> oltin gradient + yorqin dog'
    if (cov > 0) {
      const t = Math.max(0, Math.min(1, (py - (cy - R)) / (2 * R)));
      const hr = lerp(0xff, 0xf2, t), hg = lerp(0x9a, 0xb4, t), hb = lerp(0xc2, 0x7a, t);
      const hx = px - (cx - 62), hy = py - (cy - 70);
      const hl = Math.exp(-(hx * hx + hy * hy) / (2 * 95 * 95)) * 0.5;
      r = lerp(r, Math.min(255, hr + (255 - hr) * hl), cov);
      g = lerp(g, Math.min(255, hg + (255 - hg) * hl), cov);
      b = lerp(b, Math.min(255, hb + (255 - hb) * hl), cov);
    }

    // uchqunlar
    for (let i = 0; i < sparkles.length; i++) {
      const s = sparkles[i];
      const ex = px - s.x, ey = py - s.y;
      const dd = ex * ex + ey * ey;
      if (dd < s.r * s.r * 9) {
        const k = Math.exp(-dd / (s.r * s.r * 2.2)) * s.a;
        r = r + (255 - r) * k; g = g + (255 - g) * k; b = b + (255 - b) * k;
      }
    }

    raw[off++] = clamp(Math.round(r));
    raw[off++] = clamp(Math.round(g));
    raw[off++] = clamp(Math.round(b));
  }
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4);
ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  chunk("IHDR", ihdr),
  chunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
  chunk("IEND", Buffer.alloc(0)),
]);

const out = path.join(__dirname, "..", "public", "start.png");
fs.writeFileSync(out, png);
console.log(`[image] yaratildi: ${out} (${(png.length / 1024).toFixed(1)} KB, ${W}x${H})`);
