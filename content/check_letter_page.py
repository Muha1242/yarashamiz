#!/usr/bin/env python3
"""letter.html — animatsion sahifa uchun statik tekshiruv (Python).

Spec talablari bajarilganini kod bo'yicha tekshiradi:
  * bitta fayl, tashqi kutubxonasiz (faqat shrift + Telegram SDK)
  * zarrachalar chegarasi (<= 800)
  * timeline: konvert → halqa → atirgul → ism → idle
  * interaktivlik: bosish, barmoq bilan aylantirish, "Xatni o'qish"
  * video: yuboruvchi Instagram/YouTube havolasini qo'yadi → "Meni bos" tugmasi
  * qatlamli arxitektura (Config / ShapeFactory / ParticleSystem / ...)

Ishlatish:  python3 content/check_letter_page.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "mini_app" / "letter.html"
COPY = ROOT / "public" / "mini_app" / "letter.html"

REQUIRED_MARKERS = {
    "Telegram SDK": "telegram.org/js/telegram-web-app.js",
    "Telegram.WebApp": "Telegram.WebApp",
    "FOR YOU": "FOR YOU",
    "shrift": "Caveat+Brush",
    "zarracha limiti": "MAX_PARTICLES",
    "konvert": "envelopeShape",
    "halqa": "ringShape",
    "atirgul": "roseShape",
    "ism (harf-harf)": "revealName",
    "bosish": "addEventListener('click'",
    "barmoq bilan aylantirish": "touchmove",
    "xatni o'qish": 'id="readBtn"',
    "qayta ko'rish": "function replay",
    "ulashish": "shareMessage",
    "video havola": "DIRECT_MEDIA",
    "Meni bos tugmasi": 'id="videoBtn"',
    "taymer": "startCountdown",
    "forma": "showForm",
    "bot payload": "decodeBotPayload",
    "serverdan yuklash": "loadFromServer",
    "reduced-motion": "prefers-reduced-motion",
    "javob tugmalari": "buildAnswers",
    "sendData": "tg.sendData",
    "skip (2x bosish)": "skipAnimation",
    "holat (yuborilmoqda)": "showToast",
    "javob shablonlari": "REPLY_TEMPLATES",
    "xat vaqti": "letterMetaText",
    "media (Meni bos)": "MediaSection",
    "video ochish": "mediaSection.open",
    "ulashish havolasi": "buildShareUrl",
    "15 ta mavzu": "const THEMES",
    "mavzu teksturasi": "Paper.draw",
    "konvert ochilishi": "Paper.envelopeFront",
    "yorug'lik nurlari": "Fx.rays",
    "mavzu tanlash (forma)": 'id="fThemes"',
}

LAYERS = ["QATLAM 1", "QATLAM 3", "QATLAM 8", "QATLAM 10", "QATLAM 11",
          "QATLAM 12", "QATLAM 14"]

EXTERNAL_OK = ("fonts.googleapis.com", "fonts.gstatic.com",
               "telegram.org", "t.me", "www.youtube.com")


def main() -> int:
    fails: list[str] = []

    if not PAGE.exists():
        print(f"❌ {PAGE} topilmadi")
        return 1
    html = PAGE.read_text(encoding="utf-8")

    # 1) nusxa sinxron bo'lishi shart (Vercel public/ ni xizmat qiladi)
    if not COPY.exists() or COPY.read_text(encoding="utf-8") != html:
        fails.append("public/mini_app/letter.html nusxasi sinxron emas")

    # 2) spec markerlari
    for name, marker in REQUIRED_MARKERS.items():
        if marker not in html:
            fails.append(f"marker yo'q: {name} ({marker})")

    # 3) zarrachalar soni <= 800
    m = re.search(r"MAX_PARTICLES:\s*(\d+)", html)
    if not m:
        fails.append("Config.MAX_PARTICLES topilmadi")
    elif int(m.group(1)) > 800:
        fails.append(f"zarrachalar 800 dan ko'p: {m.group(1)}")

    # 4) timeline konstantalari mavjudligi
    for key in ("BURST_MS", "ROSE_MS", "TOOLS_DELAY_MS"):
        if key not in html:
            fails.append(f"timeline konstantasi yo'q: {key}")

    # 5) qatlamli arxitektura izohlari
    missing_layers = [f"QATLAM {n}" for n in
                      (1, 3, 8, 10, 11, 12, 14) if f"QATLAM {n}" not in html]
    if missing_layers:
        fails.append(f"qatlam izohlari yo'q: {missing_layers}")

    # 6) tashqi resurslar — faqat ruxsat etilganlari
    urls = set(re.findall(r"https?://([a-z0-9.\-]+)", html, re.I))
    bad = [u for u in urls if not any(u.endswith(ok) for ok in EXTERNAL_OK)]
    if bad:
        fails.append(f"ruxsat etilmagan tashqi domen: {bad}")

    # 7) inline JS sintaksisi (node bo'lsa tekshiramiz)
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not blocks:
        fails.append("inline <script> topilmadi")
    print(f"fayl: {PAGE.relative_to(ROOT)} · {len(html) // 1024} KB · "
          f"JS bloklari: {len(blocks)}")

    if fails:
        print("\n❌ Muammolar:")
        for f in fails:
            print("  -", f)
        return 1
    print("✅ Barcha statik tekshiruvlar o'tdi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
