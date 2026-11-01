"""Kanal kartalari — HAQIQIY HTML/CSS + Chromium (Playwright) render.

PIL bilan "qo'lda" chizilgan kartalar o'rniga brauzer renderi: haqiqiy shrift
(Nunito, bo'lmasa system-ui), rangli emoji (Noto Color Emoji), yumshoq
gradientlar va shisha (glass) kartalar.

Ishlatish:
    python3 content/gen_cards_html.py            # 3 kartani chizadi + nusxalaydi
    python3 content/gen_cards_html.py --no-sync  # chizadi, nusxalamaydi

Chiqish (1080x1350 @ device_scale_factor=2, viewport 540x675):
    mini_app/assets/01_qanday_ishlaydi.png
    mini_app/assets/02_imkoniyatlar.png
    mini_app/assets/03_premium.png
    (+ public/mini_app/assets/ nusxasi — faqat shu 3 fayl)
"""
from __future__ import annotations

import base64
import html
import os
import re
import shutil
import sys
import urllib.request

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "mini_app", "assets")
PUB = os.path.join(ROOT, "public", "mini_app", "assets")
LOGO = os.path.join(ROOT, "mini_app", "logo.jpg")

CHROME = "/usr/bin/chromium"
VIEW_W, VIEW_H = 540, 675           # CSS px (dizayn o'lchovi)
SCALE = 2                           # -> 1080 x 1350
TARGET = (VIEW_W * SCALE, VIEW_H * SCALE)
MIN_KB, MAX_KB = 80, 400            # rasm hajmi chegarasi

FONT_CACHE = os.path.join("/tmp", "yarashamiz_nunito.css")
FONTS_CSS_URL = ("https://fonts.googleapis.com/css2?"
                 "family=Nunito:wght@400;600;700;800&display=swap")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

CARDS = ("01_qanday_ishlaydi.png", "02_imkoniyatlar.png", "03_premium.png")


# --------------------------------------------------------------------------- #
#  Resurslar (logo + shrift) — hammasi data-URI, HTML ichida fayl yo'li yo'q
# --------------------------------------------------------------------------- #
def data_uri(path: str) -> str:
    """Rasmni base64 data-URI ga aylantiradi."""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext, "jpeg")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return "data:image/%s;base64,%s" % (mime, b64)


def font_css() -> str:
    """Nunito'ni @font-face sifatida qaytaradi (latin + latin-ext, data-URI).

    Internet bo'lmasa bo'sh satr qaytadi — CSS `system-ui` ga tushadi.
    """
    if os.path.exists(FONT_CACHE):
        try:
            with open(FONT_CACHE, encoding="utf-8") as f:
                return f.read()
        except OSError:
            pass
    blocks_out: list[str] = []
    try:
        req = urllib.request.Request(FONTS_CSS_URL, headers={"User-Agent": UA})
        css = urllib.request.urlopen(req, timeout=12).read().decode("utf-8")
        for block in re.findall(r"@font-face\s*\{[^}]*\}", css):
            # faqat lotin tillari kerak — kirill/grek/vetnam qismlarini tashlaymiz
            if "unicode-range" in block and "U+0000" not in block \
                    and "U+0100" not in block:
                continue
            m = re.search(r"url\((https://[^)]+\.woff2)\)", block)
            if not m:
                continue
            data = urllib.request.urlopen(m.group(1), timeout=15).read()
            uri = "data:font/woff2;base64," + base64.b64encode(data).decode()
            blocks_out.append(block.replace(m.group(1), uri))
    except Exception as exc:                    # oflayn — jim fallback
        print("  ! shrift yuklanmadi (%s) — system-ui ishlatiladi" % exc)
        return ""
    css = "\n".join(blocks_out)
    try:
        with open(FONT_CACHE, "w", encoding="utf-8") as f:
            f.write(css)
    except OSError:
        pass
    return css



# --------------------------------------------------------------------------- #
#  Dizayn tizimi (mini_app brend tokenlari bilan bir xil)
# --------------------------------------------------------------------------- #
BASE_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --gold:#f2b27a; --pink:#ff7aa8; --purple:#8a5cf0; --ink:#fff3f7;
  --muted:rgba(255,243,247,.76); --dim:rgba(255,243,247,.62);
  --glass:rgba(255,255,255,.08); --line:rgba(255,255,255,.18);
  --radius:28px;
}
html,body{width:540px;height:675px}
body{
  font-family:'Nunito',system-ui,-apple-system,'Segoe UI','DejaVu Sans',sans-serif;
  color:var(--ink); background:#12061c;
  -webkit-font-smoothing:antialiased; text-rendering:geometricPrecision;
  overflow:hidden;
}
.emoji{font-family:'Noto Color Emoji','Apple Color Emoji','Segoe UI Emoji',sans-serif;
       font-weight:400;font-style:normal}

/* ---------- fon: #4a1d5c -> #12061c radial + pushti/binafsha glow --------- */
.bg{position:absolute;inset:0;overflow:hidden;background:
     radial-gradient(122% 80% at 50% -18%,#5d2469 0%,#3f1553 28%,#280d38 58%,
                     #170923 80%,#12061c 100%)}
.orb{position:absolute;border-radius:50%;filter:blur(18px)}
.orb.a{width:520px;height:520px;left:-200px;top:-230px;
       background:radial-gradient(closest-side,rgba(255,122,168,.30),rgba(255,122,168,0))}
.orb.b{width:460px;height:460px;right:-180px;top:40px;
       background:radial-gradient(closest-side,rgba(138,92,240,.34),rgba(138,92,240,0))}
.orb.c{width:620px;height:380px;left:50%;bottom:-240px;transform:translateX(-50%);
       background:radial-gradient(closest-side,rgba(255,122,168,.16),rgba(255,122,168,0))}
.vig{position:absolute;inset:0;
     background:radial-gradient(88% 62% at 50% 40%,transparent 42%,
                rgba(8,2,14,.55) 100%)}

/* -------------------------------- skelet -------------------------------- */
.shell{position:relative;display:flex;flex-direction:column;
       width:540px;height:675px;padding:26px 34px 22px}
.top{display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:10px}
.logo{width:36px;height:36px;border-radius:12px;display:block;background:#1a0a26;
      border:1px solid rgba(255,255,255,.20);
      box-shadow:0 8px 22px rgba(255,122,168,.34),0 0 0 4px rgba(255,255,255,.04)}
.brand b{font-size:15px;font-weight:800;letter-spacing:.3px;
         text-shadow:0 4px 16px rgba(255,122,168,.45)}
.pill{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:800;
      letter-spacing:.2px;color:var(--gold);background:var(--glass);
      border:1px solid var(--line);border-radius:999px;padding:6px 12px;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}

.head{margin-top:24px}
.kicker{font-size:10.5px;font-weight:800;letter-spacing:1.9px;line-height:1.3;
        text-transform:uppercase;color:var(--gold)}
h1{margin-top:9px;font-size:44px;line-height:1.06;font-weight:800;letter-spacing:-.6px;
   background:linear-gradient(96deg,#ffffff 0%,#ffffff 24%,#f2b27a 60%,#ff7aa8 100%);
   -webkit-background-clip:text;background-clip:text;color:transparent;
   filter:drop-shadow(0 8px 24px rgba(255,122,168,.30))}
h1 .small{font-size:28px;letter-spacing:-.2px}
.sub{margin-top:10px;font-size:13.5px;font-weight:600;line-height:1.45;color:var(--muted)}
.rule{margin-top:15px;height:3px;width:64px;border-radius:3px;
      background:linear-gradient(90deg,#ff7aa8,#8a5cf0);
      box-shadow:0 4px 16px rgba(255,122,168,.55)}

/* ------------------------------- qatorlar ------------------------------- */
/* .list flex:0 — kontent sarlavha ostidan boshlanadi, footer pastga yopishadi */
.list{flex:0 0 auto;display:flex;flex-direction:column;gap:12px;margin-top:26px}
.row{display:flex;align-items:center;gap:14px;padding:14px 16px;
     background:var(--glass);border:1px solid var(--line);border-radius:var(--radius);
     box-shadow:0 16px 34px rgba(0,0,0,.30),
                inset 0 1px 0 rgba(255,255,255,.14),
                inset 0 -20px 34px rgba(255,255,255,.03)}
body.c1 .row{padding:18px;gap:16px}
body.c1 .txt b{font-size:18px}
body.c1 .txt span{font-size:12.8px}
/* 3 qadam — sarlavha va footer orasida teng taqsimlanadi */
body.c1 .list{flex:1 1 auto;justify-content:center;margin-top:0;gap:13px}
body.c2 .row{padding:8px 15px;gap:13px}
body.c2 .list{gap:8px;margin-top:21px}
body.c3 .row{padding:8px 15px;gap:13px}
body.c3 .list{margin-top:18px}
.num{flex:0 0 38px;width:38px;height:38px;border-radius:50%;display:flex;
     align-items:center;justify-content:center;font-size:16px;font-weight:800;color:#fff;
     background:linear-gradient(135deg,#ff7aa8,#8a5cf0);
     box-shadow:0 10px 20px rgba(160,80,220,.42),inset 0 1px 0 rgba(255,255,255,.42)}
.ico{flex:0 0 40px;width:40px;height:40px;border-radius:13px;display:flex;
     align-items:center;justify-content:center;font-size:19px;line-height:1;
     background:linear-gradient(140deg,rgba(255,122,168,.30),rgba(138,92,240,.30));
     border:1px solid rgba(255,255,255,.20);
     box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 8px 18px rgba(0,0,0,.20)}
.txt{min-width:0}
.txt b{display:block;font-size:17.5px;font-weight:800;letter-spacing:-.1px;line-height:1.2}
.txt span{display:block;margin-top:4px;font-size:12.5px;font-weight:600;
          line-height:1.4;color:var(--muted)}

/* -------------------------- badge / cta / footer ------------------------- */
.badge{align-self:flex-start;display:flex;align-items:center;gap:9px;margin-top:14px;
       padding:10px 17px;border-radius:999px;font-size:12.5px;font-weight:800;
       color:#2b0d24;letter-spacing:.1px;white-space:nowrap;
       background:linear-gradient(100deg,#f7d3a4,#ff9dbe 52%,#d79bf5);
       box-shadow:0 14px 30px rgba(255,122,168,.38),
                  inset 0 1px 0 rgba(255,255,255,.55)}
.cta{display:flex;align-items:center;gap:12px;margin-top:14px}
.cta .badge{margin-top:0}
.hint{font-size:11.5px;font-weight:600;line-height:1.35;color:var(--dim);
      letter-spacing:.1px}
.foot{margin-top:auto;padding-top:16px}
.hair{height:1px;background:linear-gradient(90deg,transparent,
      rgba(255,255,255,.20),transparent)}
.handle{margin-top:13px;text-align:center;font-size:13.5px;font-weight:800;
        letter-spacing:.4px;color:var(--gold)}
.tag{margin-top:3px;text-align:center;font-size:10.5px;font-weight:600;
     letter-spacing:.6px;color:var(--dim)}
"""


# --------------------------------------------------------------------------- #
#  Joylashuv auditi — matn kesilishi / ustma-ust tushish / chetga chiqish
# --------------------------------------------------------------------------- #
FIT_JS = """
() => {
  const bad = [];
  const vw = 540, vh = 675;
  const add = (o) => bad.push(o);

  // 1) hujjat o'lchami — kontent viewportdan chiqmasin (overflow:hidden bo'lsa ham)
  const probe = document.querySelector('.shell');
  const docH = Math.max(document.documentElement.scrollHeight, probe.scrollHeight);
  const docW = Math.max(document.documentElement.scrollWidth, probe.scrollWidth);
  if (docH > vh + 1) add({where: 'document', kind: 'vertical', value: docH + '>' + vh});
  if (docW > vw + 1) add({where: 'document', kind: 'horizontal', value: docW + '>' + vw});

  // 2) data-fit bloklari ichida matn kesilmasin
  document.querySelectorAll('[data-fit]').forEach((el) => {
    if (el.scrollHeight - el.clientHeight > 1)
      add({where: el.dataset.fit, kind: 'clipped-v',
           value: el.scrollHeight + '>' + el.clientHeight});
    if (el.scrollWidth - el.clientWidth > 1)
      add({where: el.dataset.fit, kind: 'clipped-h',
           value: el.scrollWidth + '>' + el.clientWidth});
  });

  // 3) matnli elementlar viewport chetida qolmasin
  document.querySelectorAll('.shell *').forEach((el) => {
    const txt = (el.textContent || '').trim();
    if (!txt || !el.getClientRects().length) return;
    if (el.closest('.bg')) return;
    const r = el.getBoundingClientRect();
    if (r.bottom > vh + 0.6 || r.right > vw + 0.6 || r.top < -0.6 || r.left < -0.6)
      add({where: (el.className || el.tagName), kind: 'outside',
           value: JSON.stringify({t: txt.slice(0, 20), b: +r.bottom.toFixed(1),
                                  r: +r.right.toFixed(1), top: +r.top.toFixed(1)})});
  });

  // 4) footer bilan ustma-ust tushmasin
  const foot = document.querySelector('.foot');
  if (foot) {
    const ft = foot.getBoundingClientRect().top;
    document.querySelectorAll('.list > *, .badge, .hint').forEach((b) => {
      const r = b.getBoundingClientRect();
      if (r.bottom > ft - 4)
        add({where: 'footer-overlap', kind: 'overlap',
             value: b.className + ' bottom=' + r.bottom.toFixed(1) +
                    ' footer=' + ft.toFixed(1)});
    });
  }
  return bad;
}
"""


# --------------------------------------------------------------------------- #
#  HTML yig'uvchilar
# --------------------------------------------------------------------------- #
def icon(ch: str) -> str:
    return '<span class="emoji">%s</span>' % ch


def num_row(n: int, title: str, desc: str) -> str:
    """Raqamli qadam kartasi (01 karta uchun)."""
    return ('<div class="row">'
            '<div class="num">%d</div>'
            '<div class="txt"><b>%s</b><span>%s</span></div>'
            '</div>' % (n, html.escape(title), html.escape(desc)))


def ico_row(ic: str, title: str, desc: str) -> str:
    """Ikonkali qator kartasi (02/03 kartalar uchun)."""
    return ('<div class="row">'
            '<div class="ico">%s</div>'
            '<div class="txt"><b>%s</b><span>%s</span></div>'
            '</div>' % (icon(ic), html.escape(title), html.escape(desc)))


def page(*, pill: str, kicker: str, title_html: str, sub: str, rows: str,
         logo_uri: str, fonts: str, extra: str = "", body_class: str = "",
         bg_css: str = "") -> str:
    """Umumiy karkas: brend qatori + sarlavha + qatorlar + badge + footer."""
    return ("""<!DOCTYPE html>
<html lang="uz"><head><meta charset="utf-8">
<title>Yarashamiz — karta</title>
<style>
%(fonts)s
%(css)s
%(bg)s
</style></head>
<body class="%(body_class)s">
<div class="bg"><div class="orb a"></div><div class="orb b"></div>
<div class="orb c"></div><div class="vig"></div></div>
<div class="shell">
  <div class="top">
    <div class="brand"><img class="logo" src="%(logo)s" alt="Yarashamiz">
      <b>Yarashamiz</b></div>
    <div class="pill" data-fit="pill">%(pill)s</div>
  </div>
  <div class="head" data-fit="head">
    <div class="kicker">%(kicker)s</div>
    <h1>%(title)s</h1>
    <p class="sub">%(sub)s</p>
    <div class="rule"></div>
  </div>
  <div class="list">%(rows)s</div>
  %(extra)s
  <div class="foot" data-fit="foot">
    <div class="hair"></div>
    <div class="handle">@yarashamiz_bot</div>
    <div class="tag">sevgi bilan yozilgan xatlar</div>
  </div>
</div>
</body></html>""" % {"fonts": fonts, "css": BASE_CSS, "logo": logo_uri, "bg": bg_css,
                     "body_class": body_class, "pill": pill, "kicker": kicker,
                     "title": title_html, "sub": sub, "rows": rows,
                     "extra": extra})



def cards(logo_uri: str, fonts: str, bg_css: str = "") -> list[tuple[str, str]]:
    """3 ta karta: (fayl nomi, to'liq HTML)."""
    how = page(
        logo_uri=logo_uri, fonts=fonts, bg_css=bg_css, body_class="c1",
        pill=icon("💌") + " Bot ichida",
        kicker="Yangi boshlaganlar uchun",
        title_html="Qanday ishlaydi?",
        sub="Uch qadam — 30 soniyada birinchi xat.",
        rows="".join([
            num_row(1, "Xat yozing",
                    "Mini App'da matn, taklif va shablon tanlang."),
            num_row(2, "Havolani yuboring",
                    "«Havola yaratish» → nusxalab juftingizga tashlang."),
            num_row(3, "U «Yarashamiz» desa",
                    "Juftlik ochiladi: o'yinlar, kayfiyat, biletlar."),
        ]),
    )
    feats = page(
        logo_uri=logo_uri, fonts=fonts, bg_css=bg_css, body_class="c2",
        pill=icon("✨") + " Bepul boshlanadi",
        kicker="Barchasi bitta ilovada",
        title_html="Ilova ichida",
        sub="Bepul boshlanadi — premium keyin.",
        rows="".join([
            ico_row("🎨", "15 shablon", "Klassik, Sevgi, Marmar… 10 tasi premium"),
            ico_row("🎮", "11 o'yin", "A yoki B · Moslik testi · Kim ko'proq"),
            ico_row("💫", "Kayfiyat barometri", "Kuniga 1–5: juftingiznikini ko'rasiz"),
            ico_row("📖", "Xotiralar", "Yozgan va olgan xatlar bir joyda"),
            ico_row("⏳", "Vaqt kapsulasi", "Xatni 1 oydan 1 yilgacha qulflang"),
        ]),
    )
    prem = page(
        logo_uri=logo_uri, fonts=fonts, bg_css=bg_css, body_class="c3",
        pill=icon("⭐") + " Telegram Stars",
        kicker=icon("💎") + " Premium",
        title_html='50 Stars<span class="small">/oy</span>',
        sub="Istalgan vaqtda bekor qilish mumkin.",
        rows="".join([
            ico_row("✉️", "Cheksiz xat", "Kuniga 3 ta limit yo'q — xohlaganingizcha"),
            ico_row("🎤", "Ovozli xat", "60 sekundgacha ovoz yuboring"),
            ico_row("⏳", "Vaqt kapsulasi", "Kelajakka qulflangan xat"),
            ico_row("💞", "AI maslahatchi", "Suhbatni eslab qoladigan murabbiy"),
        ]),
        extra=('<div class="cta">'
               '<div class="badge" data-fit="badge">' + icon("🎁") +
               " Yangi juftlikka 3 kun sovg'a</div>"
               '<div class="hint">Botdagi «Premium» orqali</div></div>'),
    )
    return list(zip(CARDS, (how, feats, prem)))


# --------------------------------------------------------------------------- #
#  Render + tekshiruv + nusxalash
# --------------------------------------------------------------------------- #
#  Chromium gradientlarni dithering bilan chizadi (±1 LSB shovqin) — bu PNG'ni
#  ~700 KB ga shishirib yuboradi. Shu sabab fon ikki bosqichda tayyorlanadi:
#    1) fonni alohida render qilamiz va uni kichraytirib-kattalashtirib
#       (LANCZOS → BICUBIC) shovqindan tozalaymiz — gradient silliq qoladi;
#    2) tozalangan fonni CSS `background-image` sifatida qaytarib qo'yamiz,
#       matn/emoji esa Chromium tomonidan 1:1 o'tkir chiziladi.
BG_OVERRIDE = ('.bg{background:#12061c url("%s") center/cover no-repeat!important}'
               '.orb,.vig{display:none!important}')
BG_DENOISE_GRID = (54, 68)      # 1080x1350 -> 54x68 -> 1080x1350 (shovqinsiz)


def denoise_bg(src: str, dst: str) -> str:
    """Fon renderini silliqlaydi va data-URI qaytaradi."""
    img = Image.open(src).convert("RGB")
    small = img.resize(BG_DENOISE_GRID, Image.LANCZOS)
    smooth = small.resize(TARGET, Image.BICUBIC)
    smooth.save(dst, "PNG", optimize=True)
    return data_uri(dst)


def save_png(raw: str, dest: str) -> tuple[tuple[int, int], int]:
    """Screenshot'ni RGB PNG sifatida optimallashtirib saqlaydi."""
    img = Image.open(raw).convert("RGB")
    if img.size != TARGET:
        raise SystemExit("! o'lcham xato: %s (kerak %s)" % (img.size, TARGET))
    img.save(dest, "PNG", optimize=True)
    return img.size, os.path.getsize(dest)


def render() -> list[tuple[str, tuple[int, int], int]]:
    logo_uri = data_uri(LOGO)
    fonts = font_css()
    print("  shrift: %s" % ("Nunito (data-URI)" if fonts else "system-ui fallback"))
    os.makedirs(OUT, exist_ok=True)
    result: list[tuple[str, tuple[int, int], int]] = []
    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page_obj = browser.new_page(viewport={"width": VIEW_W, "height": VIEW_H},
                                    device_scale_factor=SCALE)

        def load(markup: str) -> None:
            page_obj.set_content(markup, wait_until="load")
            page_obj.wait_for_function("document.fonts.status === 'loaded'",
                                       timeout=15000)
            page_obj.wait_for_timeout(120)      # layout/filter stabil bo'lsin

        # --- 1-bosqich: toza fon -------------------------------------------
        load(cards(logo_uri, fonts)[0][1])
        page_obj.add_style_tag(content=".shell{visibility:hidden}")
        raw_bg = "/tmp/card_bg_raw.png"
        page_obj.screenshot(path=raw_bg)
        bg_uri = denoise_bg(raw_bg, "/tmp/card_bg_smooth.png")
        print("  fon: tozalandi (%.1f KB data-URI)" % (len(bg_uri) / 1024))
        bg_css = BG_OVERRIDE % bg_uri

        # --- 2-bosqich: kartalar -------------------------------------------
        for name, markup in cards(logo_uri, fonts, bg_css):
            load(markup)
            bad = page_obj.evaluate(FIT_JS)
            tag = name.split("_")[0]
            with open("/tmp/card_%s.html" % tag, "w", encoding="utf-8") as f:
                f.write(markup)
            tmp = "/tmp/card_%s_raw.png" % tag
            page_obj.screenshot(path=tmp)
            dest = os.path.join(OUT, name)
            size, nbytes = save_png(tmp, dest)
            kb = nbytes / 1024
            print("  %-26s %dx%d  %6.1f KB" % (name, size[0], size[1], kb))
            if bad:
                for b in bad:
                    print("    ! %s: %s -> %s" % (b["where"], b["kind"], b["value"]))
                problems.append(name)
            if not MIN_KB <= kb <= MAX_KB:
                print("    ! hajm chegaradan chiqdi (%.0f–%.0f KB)" % (MIN_KB, MAX_KB))
                problems.append(name)
            result.append((name, size, nbytes))
        browser.close()
    if problems:
        raise SystemExit("! muammoli kartalar: %s" % ", ".join(sorted(set(problems))))
    return result


def sync(rows) -> None:
    """Faqat shu 3 PNG'ni public/mini_app/assets ga nusxalaydi."""
    os.makedirs(PUB, exist_ok=True)
    for name, _, _ in rows:
        shutil.copy2(os.path.join(OUT, name), os.path.join(PUB, name))
    print("  nusxa -> public/mini_app/assets (%d fayl)" % len(rows))


def main() -> None:
    print("Kartalar (HTML/CSS + Chromium, %dx%d @%dx):" %
          (VIEW_W, VIEW_H, SCALE))
    rows = render()
    if "--no-sync" not in sys.argv:
        sync(rows)
    print("tayyor ✓")


if __name__ == "__main__":
    main()

