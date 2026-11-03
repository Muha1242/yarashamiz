# Release-QA hisoboti — 2026-11-03

Tekshirilgan: `letter.html` animatsion sahifasi + reliz holati.
Muhit: prod `https://yarashamiz-two.vercel.app`, Chromium (Playwright),
390×844 / DPR 2 (iPhone 14 o'lchami). Kod o'zgartirilmadi, commit yo'q.

## 1. Smoke test (offline)

```
python3 tests/smoke.py
✅ 334 ta tekshiruv o'tdi, ❌ 0 ta
Yakuniy qator: "✅ Barcha tekshiruvlar o'tdi"
```

## 2. `mini_app/` va `public/mini_app/` sinxronligi

```
diff -r mini_app public/mini_app   → chiqish yo'q (exit 0)
```

7 ta fayl (app.js, index.html, letter.html, style.css, logo.jpg,
3 ta PNG, 05_demo.mp4) — farq yo'q.

## 3. Jonli sahifa

```
curl -o /dev/null -w '%{http_code} %{size_download}'
/mini_app/letter.html?name=Test&text=Salom
→ 200 36558
```

Qo'shimcha: prod'dagi `letter.html` repo fayli bilan **bayt-bayt bir xil**
(36558 = 36558, `diff` toza) — deploy repo bilan sinxron.
`/api/check` → `ok: true`, `warnings: []`, `BOT_TOKEN/REDIS_URL/CHANNEL_ID` = true.

## 4. Playwright — animatsiya (19/20 check ✅)

| Check | Natija |
|---|---|
| HTTP 200 | ✅ 200 |
| `window.__letter` API | ✅ `particles, start, replay, phase, name, text, music` |
| `particles` ≤ 800 | ✅ **660** |
| boshlang'ich `phase()` | ✅ 0 (ENVELOPE) |
| klik → faza ketma-ketligi | ✅ **[0, 1, 2, 3] @ [0, 68, 2088, 5124] ms** |
| `#readBtn` ko'rinishi | ✅ visible, `y=722 h=52 w=344` |
| `#toolsRow` | ✅ ko'rinadi |
| `#sheet` ochilishi | ✅ `.on`, `top=615 h=229`, matn `Salom`, meta `Kimdan: Test` |
| `#sheet` yopilishi | ✅ |
| viewport/kesilish (oddiy matn) | ✅ overflow 0, clipped 0, overlap 0 |
| gorizontal scroll | ✅ `scrollWidth 390 == innerWidth 390` |
| replay | ✅ phase 0, tugmalar yashirilgan |
| `pageerror` | ✅ **0** |
| `console.error` | ❌ 2 ta — `favicon.ico` 404 (boshqa xato yo'q) |

Faza vaqtlari `T.burst=2000`, `T.rose=3000` bilan mos: 1→2 = 2020 ms,
2→3 = 3036 ms. `#readBtn` ~6.8 s da chiqadi (IDLE + 1800 ms).

## 5. Uzun kontent (stress)

- Ism 39 belgi (`Abdurahmonjon`×3): 3 qatorga bo'linadi —
  `nameBox top=470 bottom=612`, ya'ni **atirgul/stebel ustiga tushadi**
  (08_long_name.png), so'z o'rtasidan bo'linadi (`Abdura|hmonjona`).
- Matn 929 belgi: `.sheet` 82vh chegarasida qoladi (`top=152 h=692`),
  `scrollHeight 1027 > clientHeight 691` → skroll ishlaydi.
  Lekin `#closeSheet` pastki chegarasi `bottom=1156` (>844) — birinchi
  ochilishda ko'rinmaydi, ichkarida skroll qilish kerak.
- `#letterMeta` uzun ismda kesilmaydi (`scrollWidth 350 == clientWidth 350`).
- Pageerror: 0.

## 6. Kanal (@yarashamiz_uz) — TEKSHIRILMADI

`getChat` chaqirilmadi: bu sandbox'da `BOT_TOKEN`/`CHANNEL_ID` env yo'q va
Composio'da Telegram toolkit mavjud emas (faqat discord/teams/slack/twitch/
clickup/basecamp). Shu sababli **pinned message_id yozilmaydi**, va
"video msg 26 / photo msg ~27" da'vosi mustaqil tasdiqlanmadi.
## 7. Xulosa — relizga tayyormi?

**HA, tayyor (blocker yo'q).** Smoke 334/334, deploy repo bilan bir xil,
prod 200, asosiy animatsiya (`particles=660`, faza 0→1→2→3, readBtn, sheet,
replay) ishlaydi, `pageerror` yo'q. Quyidagi 3 ta nuqta — release'dan keyingi
patch uchun, relizni to'xtatmaydi.

| # | Muammo | Daraja | Dalil |
|---|---|---|---|
| 1 | Uzun ism (≈15+ belgi) 2–3 qatorga bo'linib **atirgul/stebel bilan ustma-ust** tushadi; so'z o'rtasidan bo'linadi | O'rtacha (vizual) | `nameBox top=470 bottom=612`, 08_long_name.png |
| 2 | `favicon.ico` 404 → har ochilishda 2 ta `console.error` | Past (kosmetik) | `letter.html`da `<link rel="icon">` yo'q; funksiyaga ta'sir qilmaydi |
| 3 | Uzun matnda `#closeSheet` birinchi ochilishda ekrandan pastda (`bottom=1156 > 844`) | Past (UX) | 09_long_sheet.png; skroll bilan yetib boriladi |

Qo'shimcha kuzatuv (muammo emas): `.sheet` foni `rgba(...0.98/0.99)` bo'lgani
uchun ostidagi tugmalar juda kuchsiz ko'rinadi (yorqinlik farqi ≈0.8–4/255).
`elementFromPoint` va click-through testi sheet ustunligini tasdiqladi
(`sheetZ 7 > panelZ 5`, klik `sheetOn: true` qoldirdi) — funksional xato yo'q.

## 8. Artefaktlar

Kadrlar: `/tmp/qa_shots/00_envelope.png`, `01_burst.png`, `02_rose.png`,
`03_idle.png`, `04_readbtn.png`, `05_sheet.png`, `06_replay.png`,
`07_sheet_stack.png`, `08_long_name.png`, `09_long_sheet.png`,
`10_long_sheet_scrolled.png`.
Skriptlar: `/tmp/qa_letter.py`, `/tmp/qa_sheet.py`; JSON: `/tmp/qa_letter_report.json`.
