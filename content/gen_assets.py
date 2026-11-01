"""Kanal va bot uchun vizual kontent generatori (Pillow).

Chiqish: mini_app/assets/*.png  (+ public/mini_app/assets nusxasi)
Ishlatish:  python3 content/gen_assets.py
"""
import os
import shutil

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "mini_app", "assets")
PUB = os.path.join(ROOT, "public", "mini_app", "assets")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LOGO = os.path.join(ROOT, "mini_app", "logo.jpg")

W, H = 1080, 1350
PINK, GOLD = (255, 122, 168), (247, 201, 139)
INK, MUTED = (255, 244, 248), (255, 217, 230)


def font(size, bold=True):
    return ImageFont.truetype(FONT if bold else FONT_R, size)


def bg(w=W, h=H):
    """To'q binafsha gradient + yuqorida pushti yorug'lik."""
    img = Image.new("RGB", (w, h), (18, 6, 28))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = abs(y / max(1, h - 1) - .34)
        k = max(0.0, 1 - t * 2.1) ** 2
        d.line([(0, y), (w, y)],
               fill=(int(20 + 46 * k), int(7 + 12 * k), int(30 + 60 * k)))
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([w * .08, -h * .24, w * .92, h * .40],
                                 fill=(104, 28, 104))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    return Image.blend(img, glow, .42)


def card(img, box, radius=44, alpha=16, outline=40):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        box, radius=radius, fill=(255, 255, 255, alpha),
        outline=(255, 255, 255, outline), width=3)
    img.alpha_composite(layer)


def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def block(d, text, fnt, x, y, maxw, fill=INK, gap=10, center=False):
    for line in wrap(d, text, fnt, maxw):
        w = d.textlength(line, font=fnt)
        d.text((x + ((maxw - w) / 2 if center else 0), y), line, font=fnt, fill=fill)
        y += fnt.size + gap
    return y


def header(img, d, kicker, title, sub=None):
    d.text((90, 92), kicker.upper(), font=font(30), fill=GOLD)
    y = block(d, title, font(66), 90, 150, W - 180)
    if sub:
        y = block(d, sub, font(36, False), 90, y + 14, W - 180, fill=MUTED)
    d.rounded_rectangle([90, y + 26, 250, y + 36], radius=6, fill=PINK)


def footer(d, text="@yarashamiz_bot"):
    f = font(34)
    d.text(((W - d.textlength(text, font=f)) / 2, H - 118), text, font=f, fill=GOLD)
    f2 = font(26, False)
    sub = "sevgi bilan yozilgan xatlar"
    d.text(((W - d.textlength(sub, font=f2)) / 2, H - 70), sub, font=f2, fill=MUTED)


def numeral(d, n, cx, cy, r=52):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PINK)
    f = font(48)
    t = str(n)
    d.text((cx - d.textlength(t, font=f) / 2, cy - 34), t, font=f, fill=(30, 8, 34))


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    img.convert("RGB").save(path, "PNG", optimize=True)
    print("saved", os.path.relpath(path, ROOT), os.path.getsize(path), "bytes")


# ------------------------------------------------------- 1. QANDAY ISHLAYDI
def how_it_works():
    img = bg().convert("RGBA")
    d = ImageDraw.Draw(img)
    header(img, d, "Yangi boshlaganlar uchun", "Qanday ishlaydi?", "3 ta qadam")
    steps = [
        ("Xat yozing", "Mini App'da matn yozing, taklif va shablon tanlang."),
        ("Havolani yuboring", "«Havola yaratish» → nusxalab juftingizga tashlang."),
        ("U «Yarashamiz» desa", "Juftlik ochiladi: o'yinlar, kayfiyat, biletlar."),
    ]
    y = 430
    for i, (t, s) in enumerate(steps, 1):
        card(img, [90, y, W - 90, y + 230])
        numeral(d, i, 190, y + 115)
        yy = block(d, t, font(44), 290, y + 52, W - 400)
        block(d, s, font(31, False), 290, yy + 6, W - 400, fill=MUTED)
        y += 268
    footer(d)
    save(img, "01_qanday_ishlaydi.png")


# ------------------------------------------------------------ 2. IMKONIYATLAR
def features():
    img = bg().convert("RGBA")
    d = ImageDraw.Draw(img)
    header(img, d, "Ilova ichida", "Nimalar kutmoqda?",
           "Hammasi bitta Mini App'da — bepul boshlanadi")
    items = [
        ("15 shablon", "Marmar, Neon, Oltin, Sevgi… 10 tasi premium"),
        ("11 o'yin", "A yoki B · Kim ko'proq · Chuqur savollar · Moslik testi"),
        ("Kayfiyat barometri", "Kuniga 1-5 — juftingiznikini ko'rasiz"),
        ("Xotiralar", "Yozgan/olgan xatlar va vaqt kapsulasi"),
    ]
    y = 440
    for t, s in items:
        card(img, [90, y, W - 90, y + 172])
        d.rounded_rectangle([130, y + 52, 140, y + 122], radius=5, fill=PINK)
        yy = block(d, t, font(40), 180, y + 40, W - 330)
        block(d, s, font(29, False), 180, yy - 2, W - 330, fill=MUTED)
        y += 192
    footer(d)
    save(img, "02_imkoniyatlar.png")


# ---------------------------------------------------------------- 3. PREMIUM
def premium():
    img = bg().convert("RGBA")
    d = ImageDraw.Draw(img)
    header(img, d, "Premium", "50 Stars / oy",
           "Yangi juftlikka birinchi 3 kun — sinov sovg'a")
    rows = [
        ("Cheksiz xat", "kuniga 3 ta limit o'rniga — xohlaganingizcha"),
        ("Ovozli xat", "/voice — 60 sekundgacha, juftingizga boradi"),
        ("Vaqt kapsulasi", "1 oydan 1 yilgacha qulflangan xat"),
        ("AI maslahatchi", "/maslahat — suhbatni eslab qoladigan murabbiy"),
    ]
    y = 450
    for t, s in rows:
        card(img, [90, y, W - 90, y + 142], alpha=20)
        yy = block(d, t, font(38), 140, y + 26, W - 280)
        block(d, s, font(28, False), 140, yy - 2, W - 280, fill=MUTED)
        y += 160
    d.rounded_rectangle([90, 1102, W - 90, 1186], radius=38,
                        fill=(255, 122, 168, 46),
                        outline=(255, 255, 255, 80), width=3)
    f = font(36)
    t = "Botdagi «Premium» tugmasi orqali"
    d.text(((W - d.textlength(t, font=f)) / 2, 1126), t, font=f, fill=INK)
    if os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGBA").resize((150, 150), Image.LANCZOS)
        mask = Image.new("L", (150, 150), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, 150, 150], radius=34, fill=255)
        img.paste(lg, (W - 250, 92), mask)
    footer(d)
    save(img, "03_premium.png")


if __name__ == "__main__":
    how_it_works()
    features()
    premium()
    os.makedirs(PUB, exist_ok=True)
    for f in sorted(os.listdir(OUT)):
        shutil.copy2(os.path.join(OUT, f), os.path.join(PUB, f))
    print("synced ->", os.path.relpath(PUB, ROOT))

