#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yarashamiz Mini App — HAQIQIY ekran yozuvi (Playwright + Chromium) → MP4.

PIL bilan "qo'lda chizilgan" video emas: haqiqiy `mini_app/` UI brauzerda
ochiladi, Telegram WebApp SDK stub + `/api/app` mock bilan ishlaydi va
Playwright'ning video-recorder'i orqali 720x1560 (360x780 @2x) webm yoziladi,
keyin `imageio_ffmpeg` bilan H.264 / yuv420p / 30fps MP4 ga o'giriladi.

Ishga tushirish:
    python3 content/make_video.py

Natija:
    mini_app/assets/05_demo.mp4
    public/mini_app/assets/05_demo.mp4
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
CHROMIUM = "/usr/bin/chromium"
PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"
APP_URL = f"{BASE}/mini_app/"
VID_DIR = Path("/tmp/vid")
OUT_MAIN = ROOT / "mini_app" / "assets" / "05_demo.mp4"
OUT_COPY = ROOT / "public" / "mini_app" / "assets" / "05_demo.mp4"
MAX_BYTES = 4 * 1024 * 1024

# --- sahna vaqtlari (soniya) ---
T_SPLASH = 2.2        # splash animatsiyasi
T_WRITE = 1.1         # yozish tab (default) tinch ko'rinish
SCROLL_STEPS = 20     # sekin scroll: 20 * 9px = 180px (sahifa ~221px scroll bo'ladi)
SCROLL_DELTA = 9
SCROLL_PAUSE = 0.04
T_SCROLL_SETTLE = 0.25
T_ME = 1.7            # Hisobim tab
T_GAMES = 1.7         # O'yinlar tab
T_LETTER_OPEN = 3.8   # konvert bosilgandan keyingi sahna (ochilish animatsiyasi bilan)
DUR_MAX = 19.6        # 12–20s talabi uchun xavfsiz yuqori chegara

# --- Telegram WebApp stub (initData BO'SH EMAS bo'lishi shart) ---
TG_STUB = """
window.Telegram = { WebApp: {
  initData: 'demo',
  initDataUnsafe: { user: { id: 1, first_name: 'Dilnoza' } },
  ready() {}, expand() {}, close() {},
  sendData() {}, onEvent() {}, offEvent() {},
  colorScheme: 'dark', themeParams: {},
  setHeaderColor() {}, setBackgroundColor() {},
  HapticFeedback: {
    impactOccurred() {}, notificationOccurred() {}, selectionChanged() {}
  },
  MainButton: { hide() {}, show() {} },
  BackButton: { show() {}, hide() {}, onClick() {} },
  openTelegramLink() {}, openLink() {}, closeApp() {}
} };
"""

# --- /api/app mock javoblari ---
MOCK = {
    "me": {
        "ok": True,
        "user": {"id": 1, "name": "Dilnoza"},
        "pair": True, "partner": "Aziz", "pts": 184, "streak": 7,
        "prem": True, "premDays": 24, "letters": 12, "days": 41,
        "prices": {"month": 50, "year": 500, "gift": 80},
        "mission": "Birga 15 daqiqa suhbat", "themeCount": 15,
        "refs": 1, "refsOk": 1, "remind": True,
        "invite": "https://t.me/yarashamiz_bot?start=ref_1",
        "mood": 4, "partnerMood": 5,
        "moodIcons": {"1": "\U0001F622", "2": "\U0001F615", "3": "\U0001F610",
                      "4": "\U0001F642", "5": "\U0001F60D"},
    },
    "form": {
        "ok": True, "isPrem": True, "left": None, "limit": 3, "textMax": 300,
        "offers": ["Kino", "Kofe", "Sayr"],
        "themes": [
            {"id": "classic", "name": "Klassik", "prem": False, "ok": True},
            {"id": "marmar", "name": "Marmar", "prem": False, "ok": True},
            {"id": "neon", "name": "Neon", "prem": True, "ok": True},
        ],
    },
    "games": {
        "ok": True, "pair": True, "pts": 184,
        "games": [
            {"id": "ab", "name": "A yoki B", "n": 5, "mode": "guess",
             "prem": False, "done": False, "him": True,
             "qs": [["Kino yoki kofe?", "Kino", "Kofe"]]},
            {"id": "kq", "name": "\U0001F4AC Kunlik savol", "n": 1, "mode": "talk",
             "prem": False, "done": False, "him": False,
             "qs": ["Bugun birga nima qilsak, ajoyib kun bo'ladi?"]},
        ],
    },
    # GET /api/app (initData yo'q) → bot nomi
    "bot": {"ok": True, "bot": "yarashamiz_bot"},
}

LETTER_PAYLOAD = {
    "t": "Kechir meni. Seni juda sog'indim.",
    "o": ["Kino", "Kofe"],
    "theme": "love",
    "n": "Aziz",
}

notes: list[str] = []
T0: float = 0.0


def note(msg: str) -> None:
    el = (time.time() - T0) if T0 else 0.0
    notes.append(msg)
    print(f"[video] {el:5.2f}s {msg}", flush=True)


def wait(page, sec: float) -> None:
    page.wait_for_timeout(int(round(sec * 1000)))



# ============================ lokal server ============================
def start_server() -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=str(PUBLIC),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("http.server darhol to'xtadi (port band?)")
        try:
            with urllib.request.urlopen(f"{BASE}/mini_app/index.html", timeout=1) as r:
                if r.status == 200:
                    return proc
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.15)
    stop_server(proc)
    raise RuntimeError(f"lokal server {PORT}-portda ishga tushmadi")


def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ============================ mock / route ============================
def handle_api(route) -> None:
    req = route.request
    action = ""
    if req.method == "POST":
        try:
            action = (json.loads(req.post_data or "{}") or {}).get("action") or ""
        except (ValueError, TypeError):
            action = ""
    payload = MOCK.get(action) or MOCK["bot"]
    route.fulfill(
        status=200,
        content_type="application/json; charset=utf-8",
        body=json.dumps(payload, ensure_ascii=False),
    )


def handle_sdk(route) -> None:
    """Haqiqiy telegram-web-app.js `window.Telegram.WebApp` ni almashtirib,
    initData ni bo'sh qiladi → ilova 'botdan oching' kartasini ko'rsatadi.
    Shuning uchun SDK o'rniga bo'sh javob beramiz: stub o'z joyida qoladi."""
    route.fulfill(status=200, content_type="application/javascript", body="/* stubbed */")


def view_heading(page) -> str:
    return page.evaluate(
        """() => {
          const h2 = document.querySelector('#view .card h2');
          if (h2) return h2.textContent.trim();
          const v = document.querySelector('#view');
          return (v ? v.innerText : '').replace(/\\s+/g, ' ').trim().slice(0, 90);
        }"""
    )


def assert_real_ui(page, scene: str) -> str:
    body = page.evaluate("() => document.body.innerText")
    if "Ilovani botdan oching" in body or "Ilovani qayta oching" in body:
        raise RuntimeError(f"{scene}: auth/xato kartasi chiqdi — stub yoki mock ishlamadi")
    head = view_heading(page)
    note(f"{scene}: «{head}»")
    return head


# ============================ ekran yozuvi ============================
def slow_scroll(page) -> None:
    """Inson barmog'iday sekin scroll: kichik wheel qadamlar + pauza."""
    page.mouse.move(180, 420)
    for _ in range(SCROLL_STEPS):
        page.mouse.wheel(0, SCROLL_DELTA)
        page.wait_for_timeout(int(SCROLL_PAUSE * 1000))


def record(browser):
    """Haqiqiy UI ni yozib oladi; sahifa videolari ro'yxatini qaytaradi."""
    global T0
    T0 = time.time()
    ctx = browser.new_context(
        viewport={"width": 360, "height": 780},
        device_scale_factor=2,
        record_video_dir=str(VID_DIR),
        record_video_size={"width": 720, "height": 1560},
        locale="uz-UZ",
    )
    ctx.add_init_script(TG_STUB)
    ctx.route("**/api/app*", handle_api)
    ctx.route("https://telegram.org/js/telegram-web-app.js", handle_sdk)

    videos = []
    try:
        # ---------- 1-4: asosiy ekran: splash → Yozish → Hisobim → O'yinlar ----------
        page = ctx.new_page()
        videos.append(page.video)
        page.goto(APP_URL, wait_until="load", timeout=30000)
        try:  # shrift almashishi yozuv o'rtasida bo'lmasin
            page.evaluate("document.fonts.ready.then(() => true)")
        except Exception:  # noqa: BLE001 - font API bo'lmasa ham davom
            pass

        # 1) splash
        page.wait_for_selector("#splash", state="attached", timeout=5000)
        note("sahna 1: splash (2.2s)")
        wait(page, T_SPLASH)
        page.wait_for_selector("#splash", state="detached", timeout=6000)

        # 2) Yozish tab (default)
        page.wait_for_selector("#view .card", timeout=8000)
        wait(page, T_WRITE)
        assert_real_ui(page, "sahna 2: Yozish tab")
        scroll_h = page.evaluate("() => document.scrollingElement.scrollHeight")
        note(f"sahna 2: scroll balandligi {scroll_h}px (viewport 780px)")
        slow_scroll(page)
        wait(page, T_SCROLL_SETTLE)

        # 3) Hisobim
        page.click('.tabs button[data-tab="me"]')
        wait(page, T_ME)
        assert_real_ui(page, "sahna 3: Hisobim tab")

        # 4) O'yinlar
        page.click('.tabs button[data-tab="games"]')
        wait(page, T_GAMES)
        assert_real_ui(page, "sahna 4: O'yinlar tab")
        page.close()

        # ---------- 5: xat sahnaSi (?d= havola) ----------
        payload = base64.urlsafe_b64encode(
            json.dumps(LETTER_PAYLOAD, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        letter_url = f"{APP_URL}?d={payload}"

        page2 = ctx.new_page()
        videos.append(page2.video)
        page2.goto(letter_url, wait_until="load", timeout=30000)
        # ikkinchi splash videosida takrorlanmasin (dublikat taassurot bermasin)
        try:
            page2.evaluate("() => { const s = document.getElementById('splash');"
                           " if (s) s.remove(); }")
        except Exception:  # noqa: BLE001
            pass
        try:
            page2.evaluate("document.fonts.ready.then(() => true)")
        except Exception:  # noqa: BLE001
            pass
        page2.wait_for_selector(".scene .envelope", timeout=8000)
        envelope = page2.wait_for_selector(".scene .envelope", timeout=8000)
        note("sahna 5: xat konverti ko'rindi")
        box = envelope.bounding_box()
        if not box:
            raise RuntimeError("sahna 5: konvert o'lchami olinmadi")
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        # konvert suzish animatsiyasida — Playwright'ning "stability" tekshiruvi
        # kutib qoladi, shuning uchun haqiqiy sichqoncha bosishini koordinataga beramiz
        page2.mouse.move(cx, cy, steps=4)
        wait(page2, 0.4)
        t_click = time.time()
        page2.mouse.click(cx, cy)
        wait(page2, 1.05)  # ilova 900ms dan keyin `.lstage` ni ko'rsatadi
        if not page2.query_selector(".lstage"):  # zaxira: to'g'ridan-to'g'ri click
            page2.evaluate("() => { const e = document.querySelector('.scene .envelope');"
                           " if (e) e.click(); }")
            wait(page2, 0.6)
        note("sahna 5: konvert bosildi → ochilish sahnasi")
        remain = T_LETTER_OPEN - (time.time() - t_click)
        if remain > 0:
            wait(page2, remain)
        opened = page2.evaluate(
            """() => {
              const st = document.querySelector('.lstage');
              if (!st) return '';
              const t = st.querySelector('.ltext');
              return (t ? t.innerText : '').replace(/\\s+/g, ' ').trim();
            }"""
        )
        if not opened:
            raise RuntimeError("sahna 5: xat ochilish sahnasi (.lstage) chiqmadi")
        note(f"sahna 5: ochilgan xat matni «{opened}»")
    finally:
        ctx.close()  # videolarni yakunlaydi

    paths = []
    for v in videos:
        try:
            paths.append(Path(v.path()))
        except Exception as exc:  # noqa: BLE001
            note(f"video yo'li olinmadi: {exc}")
    return [p for p in paths if p.exists()]


# ============================ ffmpeg: MP4 ============================
def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def encode(webms, out: Path, crf: int, cap: float | None = None) -> None:
    """webm(lar) → H.264 / yuv420p / 30fps / faststart MP4 (cap = maks. davomiylik)."""
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    if len(webms) == 1:
        cmd += ["-i", str(webms[0]), "-vf", "scale=720:-2"]
    else:
        chains, labels = [], []
        for i, p in enumerate(webms):
            cmd += ["-i", str(p)]
            chains.append(f"[{i}:v]scale=720:-2,setsar=1,fps=30[v{i}]")
            labels.append(f"[v{i}]")
        fc = ";".join(chains) + ";" + "".join(labels) + \
            f"concat=n={len(webms)}:v=1:a=0[v]"
        cmd += ["-filter_complex", fc, "-map", "[v]"]
    cmd += [
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart",
    ]
    if cap:
        cmd += ["-t", f"{cap:.2f}"]
    cmd.append(str(out))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg xato:\n{res.stderr[-1500:]}")


def probe(path: Path) -> dict:
    """ffprobe yo'q muhitda ham ishlaydi: `ffmpeg -i` chiqishini o'qiymiz."""
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True)
    err = res.stderr or ""
    info = {"duration": None, "width": None, "height": None, "fps": None,
            "codec": None, "pix_fmt": None}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if m:
        info["duration"] = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                            + float(m.group(3)))
    m = re.search(r"Video:\s*(\w+)\(?.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        info["codec"] = m.group(1)
        info["width"], info["height"] = int(m.group(2)), int(m.group(3))
    m = re.search(r"(\d+(?:\.\d+)?)\s+fps", err)
    if m:
        info["fps"] = float(m.group(1))
    m = re.search(r"Video:.*?(yuv\d+p(?:\([^)]*\))?)", err)
    if m:
        info["pix_fmt"] = m.group(1)
    info["bytes"] = path.stat().st_size
    return info


def grab_frames(mp4: Path, times: list[float]) -> list[Path]:
    out = []
    for i, t in enumerate(times, start=1):
        png = Path(f"/tmp/vframe{i}.png")
        subprocess.run(
            [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", str(png)],
            check=True, capture_output=True, text=True,
        )
        out.append(png)
        print(f"[video] kadr {i}: t={t:.2f}s → {png}", flush=True)
    return out


def ensure_recorder_ffmpeg() -> None:
    """Playwright video-recorder o'z ffmpeg nusxasini talab qiladi (sistem ffmpeg
    yetmaydi). Yo'q bo'lsa bir marta yuklab olamiz — skript qayta ishlashi uchun."""
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
                or (Path.home() / ".cache" / "ms-playwright"))
    if list(root.glob("ffmpeg-*/ffmpeg*")):
        return
    print("[video] playwright record uchun ffmpeg yuklanmoqda…", flush=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "ffmpeg"], check=False)


def main() -> int:
    ensure_recorder_ffmpeg()
    if VID_DIR.exists():
        shutil.rmtree(VID_DIR, ignore_errors=True)
    VID_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MAIN.parent.mkdir(parents=True, exist_ok=True)
    OUT_COPY.parent.mkdir(parents=True, exist_ok=True)

    server = start_server()
    webms: list[Path] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=CHROMIUM,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--hide-scrollbars", "--force-color-profile=srgb",
                      # video-recorder oynani qurilma piksellarida oladi: usiz
                      # 360x780 kadr 720x1560 kanvasga surat bilan (xira) cho'ziladi
                      "--force-device-scale-factor=2"],
            )
            try:
                webms = record(browser)
            finally:
                browser.close()
    finally:
        stop_server(server)

    if not webms:
        raise RuntimeError("/tmp/vid ichida webm yozuvi topilmadi")
    webms = sorted(webms, key=lambda p: p.stat().st_mtime)
    for p in webms:
        print(f"[video] webm: {p} ({p.stat().st_size / 1024:.0f} KB)", flush=True)

    tmp = Path("/tmp/05_demo.mp4")
    chosen_crf = 20
    for crf in (20, 23, 26):
        encode(webms, tmp, crf)
        info = probe(tmp)
        dur = info["duration"] or 0.0
        if dur > DUR_MAX:  # 20s dan oshib ketmasin (xat sahnaS oxirida kesiladi)
            print(f"[video] {dur:.2f}s > {DUR_MAX}s → kesiladi", flush=True)
            encode(webms, tmp, crf, cap=DUR_MAX)
            info = probe(tmp)
            dur = info["duration"] or 0.0
        chosen_crf = crf
        print(f"[video] crf {crf} → {info['bytes'] / 1024 / 1024:.2f} MB, "
              f"{dur:.2f}s", flush=True)
        if info["bytes"] < MAX_BYTES:
            break

    shutil.copyfile(tmp, OUT_MAIN)
    shutil.copyfile(tmp, OUT_COPY)

    info = probe(OUT_MAIN)
    dur = info["duration"] or 0.0
    frames = grab_frames(OUT_MAIN, [1.2, min(6.5, dur * 0.45),
                                    max(0.1, dur - 2.0)])

    print("\n===== NATIJA =====")
    print(f"fayl:        {OUT_MAIN}")
    print(f"nusxa:       {OUT_COPY}")
    print(f"webm soni:   {len(webms)}")
    print(f"duration:    {dur:.2f}s  (talab 12–20s: "
          f"{'OK' if 12 <= dur <= 20 else 'XATO'})")
    print(f"resolution:  {info['width']}x{info['height']}")
    print(f"codec/fps:   {info['codec']} / {info['fps']} / {info['pix_fmt']}")
    print(f"hajm:        {info['bytes'] / 1024 / 1024:.2f} MB "
          f"({'OK' if info['bytes'] < MAX_BYTES else 'XATO'})")
    print(f"crf:         {chosen_crf}")
    print(f"kadrlar:     {', '.join(str(p) for p in frames)}")
    print("sahnalar:")
    for n in notes:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


