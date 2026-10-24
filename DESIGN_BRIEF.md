# 🎨 Yarashamiz — dizayn brifi (dizayner sessiyasi uchun)

Bu fayl dizayn bo'yicha ishlaydigan sherik uchun. Maqsad: mavjud mantiqni
buzmasdan vizual sifatni oshirish. Tuzatishlar `cline/7x6v96sq` branch'ida,
PR #34.

## 1. Stack va fayllar

| Nima | Fayl |
|---|---|
| Mini App (Telegram WebView) | `mini_app/index.html`, `mini_app/app.js`, `mini_app/style.css` |
| Nusxa (Vercel xizmat qiladi) | `public/mini_app/*` — **har o'zgarishdan keyin `cp` bilan sinxronlash shart** |
| Bot matnlari / tugmalar | `bot.py` (faqat matn, dizayn emas) |
| Testlar | `tests/smoke.py` (98 ta) |

Faqat HTML/CSS/JS. **Yangi kutubxona, framework, CDN qo'shilmaydi** (Telegram
WebView + Vercel tezligi uchun). Tashqi shrift allaqachon bor: Caveat + Nunito.

## 2. Ekranlar

1. **Yozish** (`viewWrite` → `buildForm`) — matn, takliflar, dizayn tanlash, havola.
2. **Hisobim** (`viewMe`) — streak, ball, premium, kunlik savol, referral, eslatma.
3. **O'yinlar** (`viewGames` / `playGame` / `submit`) — savol kartasi, progress bar.
4. **Xotiralar** (`viewMemory`) — xatlar ro'yxati.
5. **Bog'im** (`viewGarden`) — o'simlik bosqichlari, 28 kunlik gulzor.
6. **Xat ochish** (`letterOpen`) — 3D konvert, «Yarashamiz», javob, rasm, shikoyat.

## 3. Dizayn tokenlari (hozirgi)

```css
:root{
  --gold:#f2b27a; --pink:#ff7aa8; --purple:#8a5cf0; --ink:#fff3f7;
  --glass:rgba(255,255,255,.09); --line:rgba(255,255,255,.18); --ok:#7be0a8;
}
body{ background: radial-gradient(...#4a1d5c,#2a0f3d 45%,#12061c) }
```

Klasslar: `.card`, `.btn.btn-main`, `.btn.btn-ghost`, `.btn-sm`, `.stat`,
`.stat-grid`, `.tabs`, `.qbar`, `.ttext`, `.tbtn`, `.badge`, `.mem`, `.game`.

Kontrast qoidasi: matn fon ustida **kamida 4.5:1**. Yorqin (marmar) fonlarda
matn `#243044`.

## 4. Xat dizaynlari (themes)

12 ta mavzu bor; **yangi «Marmar 🤍» (bepul) qo'shildi**. Mavzu qo'shish tartibi:

1. `bot.py` → `THEMES` ro'yxati: `("marmar", "Marmar 🤍")`.
   Premium bo'lsa — `PREMIUM_THEMES` ga ham qo'shiladi.
2. `mini_app/app.js` → `THEME_NAMES` (nom) + `CARD_COLORS` (PNG karta gradienti)
   + yorqin fon uchun `CARD_INK`.
3. `mini_app/style.css` → `.card.theme-<id>` va `.pl-inner.theme-<id>`
   (+ kerak bo'lsa `.pl-inner.theme-<id> .pl-text` rangi).
4. `cp mini_app/* public/mini_app/` → `diff -r mini_app public/mini_app`.
5. `python3 tests/smoke.py` (mavzu testlari bor).

Yangi mavzu g'oyalari: «Binafsha tun», «Qog'oz» (texture), «Yulduzli osmon»,
«Oltin ramka», «Suv rang» (watercolor). Premium mavzular monetizatsiya uchun.

## 5. Nima o'zgartirsa bo'ladi / bo'lmaydi

✅ Ranglar, gradientlar, soyalar, radius, shrift o'lchami, animatsiya, konvert
   effekti, kartalar joylashuvi, ikonkalar (emoji o'rniga SVG bo'lsa ham).
✅ Yangi mavzu qo'shish (4-bo'limdagi tartib bilan).

❌ **ID va klass nomlarini o'zgartirmaslik**: `#view`, `#pill`, `#tabs`,
   `#confetti`, `.hearts`, `.tabs button[data-tab]`, `.pl-inner`, `.pl-text`,
   `.theme-*`, `.qbar`, `.qtext`, `.qopt`. JS shularga tayanadi.
❌ `app.js` dagi API chaqiruvlari (`api('me')`, `api('answer')`, `sendData`) va
   `data-*` atributlarini o'zgartirmaslik.
❌ `bot.py`/`store.py`/`api/*` mantiqini o'zgartirmaslik — faqat matn bo'lsa,
   alohida kelishamiz.
❌ Tashqi kutubxona/CDN, og'ir rasm/font (Mini App 2 sekundda ochilishi kerak).

## 6. Texnik cheklovlar

- Telegram WebView (iOS/Android): `position:fixed` + `env(safe-area-inset-*)`,
  `100vh` o'rniga `min-height:100vh`, `backdrop-filter` iOS'da sekin bo'lishi mumkin.
- Animatsiyalar `transform/opacity` bilan (layoutni qayta hisoblashsiz).
- Rasm yuklash yo'q — hammasi CSS/canvas.
- `prefers-reduced-motion` qo'llab-quvvatlansa yaxshi.
- Matn o'zbek lotinida, qisqa (xat 300 belgi, taklif 40 belgi).

## 7. Tekshirish ro'yxati (har PR oldidan)

```bash
node --check mini_app/app.js && node --check public/mini_app/app.js
diff -r mini_app public/mini_app        # farq bo'lmasin
python3 tests/smoke.py                  # 98/98
```
Qo'lda: 360×640 va 390×844 da yozish/ochish/o'yin ekranlari; yorqin mavzuda
matn o'qilishi; iOS safe-area; konvert animatsiyasi; PNG karta.

## 8. Hozirgi holat

- «Marmar» mavzusi qo'shildi (bepul): oq-ko'k qog'oz, to'q matn, PNG kartada
  ham to'g'ri rang.
- Qolgan dizayn ishlari: umumiy palitra, konvert sahnasi, o'yin kartalari,
  «Bog'im» illustratsiyasi, ikonkalar.
