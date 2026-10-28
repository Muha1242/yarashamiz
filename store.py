"""Yarashamiz v3.1 (Vercel/webhook) — ma'lumotlar qatlami: Upstash Redis.

v3.1 qo'shimchalari:
- "kq" (Kunlik savol) o'yini
- admin uchun statistika (admin_stats)
- juftlik/premium hisoblagichlari
"""
import datetime as dt
import json
import os
import secrets
import time
from contextlib import contextmanager

import redis

r = redis.from_url(
    os.environ["REDIS_URL"], decode_responses=True,
    socket_timeout=5, socket_connect_timeout=5,
    retry_on_timeout=True, health_check_interval=30)

# Server (Vercel) UTC'da ishlaydi, foydalanuvchilar esa O'zbekistonda (UTC+5).
# Kunlik savol / seriya / eslatmalar mahalliy vaqt bo'yicha hisoblanishi kerak.
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "5"))


def now():
    """Mahalliy (Toshkent) vaqt."""
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=TZ_OFFSET)


def today():
    """Mahalliy sana (YYYY-MM-DD)."""
    return now().date().isoformat()


def day_start_ts():
    """Mahalliy yarim tun (epoch soniyada) — kunlik limit uchun."""
    local_midnight = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return int((local_midnight - dt.timedelta(hours=TZ_OFFSET)).timestamp())

GAMES = {
    "ab": {"name": "A yoki B", "n": 5, "mode": "guess"},
    "wh": {"name": "Kim ko'proq?", "n": 5, "mode": "match"},
    "ms": {"name": "Kunlik missiya", "n": 1, "mode": "mission"},
    "kq": {"name": "💬 Kunlik savol", "n": 1, "mode": "talk"},
    "qz": {"name": "Sevgi kvizi", "n": 6, "mode": "match", "prem": True},
}


def _pid(a, b):
    return f"{min(a, b)}:{max(a, b)}"


# ------------------------------- JUFTLIK --------------------------------
def pair_of(u):
    """(pid, a, b) yoki None."""
    m = r.get(f"mate:{u}")
    if not m:
        return None
    try:
        o = int(m)
    except (TypeError, ValueError):
        return None
    return (_pid(u, o), u, o)


def set_name(u, name):
    """Profil ismi (juftlikka ko'rsatish uchun)."""
    name = (name or "").strip()[:40]
    if name:
        r.set(f"name:{u}", name)


def other(p, u):
    return p[2] if p[1] == u else p[1]


def add_pair(a, b):
    r.set(f"mate:{a}", b)
    r.set(f"mate:{b}", a)
    r.set(f"mets:{_pid(a, b)}", int(time.time()))
    if r.set(f"pairdone:{_pid(a, b)}", 1, nx=True):   # har juftlik bir marta
        r.incr("cnt:pairs")
        r.incr(f"cnt:pairs:{today()}")


def pair_ts(a, b):
    return int(r.get(f"mets:{_pid(a, b)}") or 0)


def add_pts(pid, pts):
    r.incrby(f"pts:{pid}", pts)


def get_pts(pid):
    return int(r.get(f"pts:{pid}") or 0)


# -------------------------------- XATLAR --------------------------------
def add_letter(sender, text, offers, theme):
    lid = r.incr("seq:letters")
    r.hset(f"letter:{lid}", mapping={
        "sender": sender, "text": text, "offers": json.dumps(offers),
        "theme": theme, "ts": int(time.time()), "receiver": "", "thn": 0})
    r.sadd(f"mine:{sender}", lid)
    r.incr(f"cnt:letters:{today()}")
    return lid


def letter(lid):
    if lid is None or lid == "":
        return None
    d = r.hgetall(f"letter:{lid}")
    if not d or "sender" not in d:
        return None
    try:
        offers = json.loads(d.get("offers") or "[]")
    except Exception:  # noqa: BLE001
        offers = []
    return {"id": int(lid), "sender": int(d["sender"]), "text": d.get("text", ""),
            "offers": offers, "theme": d.get("theme") or "classic",
            "ts": int(d.get("ts") or 0), "receiver": int(d.get("receiver") or 0),
            "thn": int(d.get("thn") or 0)}


def set_receiver(lid, u):
    r.hset(f"letter:{lid}", "receiver", u)
    r.sadd(f"got:{u}", lid)


THEME_LIMIT = 3


def set_theme(lid, theme):
    """Xat mavzusini o'zgartiradi.

    Qaytaradi: yangi thn (1..3), 0 = limit tugagan, -1 = xat topilmadi.
    """
    h = f"letter:{lid}"
    if not r.exists(h):
        return -1
    n = int(r.hget(h, "thn") or 0)
    if n >= THEME_LIMIT:
        return 0
    r.hset(h, mapping={"theme": theme, "thn": n + 1})
    return n + 1


def last_mine(u):
    """Foydalanuvchi yozgan eng oxirgi xat."""
    ids = [int(x) for x in r.smembers(f"mine:{u}")]
    rows = [letter(i) for i in ids]
    rows = [x for x in rows if x]
    if not rows:
        return None
    rows.sort(key=lambda x: x["ts"], reverse=True)
    return rows[0]


def count_today_letters(u, since_ts):
    ids = [int(x) for x in r.smembers(f"mine:{u}")]
    if not ids:
        return 0
    pipe = r.pipeline()
    for i in ids:
        pipe.hget(f"letter:{i}", "ts")
    return sum(1 for ts in pipe.execute() if ts and int(ts) > since_ts)


def count_letters(u):
    return r.scard(f"mine:{u}")


def my_library(u, limit=20):
    ids = [int(x) for x in r.sunion(f"mine:{u}", f"got:{u}")]
    rows = [x for x in (letter(i) for i in ids) if x]
    rows.sort(key=lambda x: x["ts"], reverse=True)
    return rows[:limit]


# -------------------------------- BLOK ----------------------------------
def is_blocked(u, sender):
    return r.exists(f"blocked:{u}:{sender}") == 1


def block(u, sender):
    r.set(f"blocked:{u}:{sender}", 1)


# ------------------------------ O'YINLAR --------------------------------
def get(pid, g, u):
    d = r.get(f"ans:{pid}:{today()}:{g}:{u}")
    return json.loads(d) if d else None


def put(pid, g, u, d):
    r.set(f"ans:{pid}:{today()}:{g}:{u}", json.dumps(d))


def done(pid, g, u):
    d, gg = get(pid, g, u), GAMES[g]
    if d is None:
        return False
    return len(d) >= gg["n"] if gg["mode"] != "mission" else bool(d.get("ok"))


# ------------------------------- QULF -----------------------------------
@contextmanager
def lock(key, ttl=15):
    """Qisqa muddatli Redis qulfi (ikki marta ball qo'shilmasligi uchun).

    `with lock("nom") as ok:` — ok True bo'lsagina amal bajariladi.
    """
    token = secrets.token_hex(8)
    full = f"lock:{key}"
    got = bool(r.set(full, token, nx=True, ex=ttl))
    try:
        yield got
    finally:
        if got:
            try:
                if r.get(full) == token:
                    r.delete(full)
            except Exception:  # noqa: BLE001
                pass


# ------------------------------- SERIYA ---------------------------------
def touch(u):
    t, cur = today(), r.hgetall(f"streak:{u}")
    if not cur:
        n = 1
        r.hset(f"streak:{u}", mapping={"last": t, "n": 1})
        r.sadd("users", u)          # faqat yangi foydalanuvchida
        r.sadd(f"new:{t}", u)
    elif cur["last"] == t:
        n = int(cur["n"])
    else:
        y = (now().date() - dt.timedelta(1)).isoformat()
        n = int(cur["n"]) + 1 if cur["last"] == y else 1
        r.hset(f"streak:{u}", mapping={"last": t, "n": n})
    r.sadd(f"active:{t}", u)        # bugungi faol foydalanuvchilar
    r.expire(f"active:{t}", 400 * 86400)
    if not cur:
        r.expire(f"new:{t}", 400 * 86400)
    return n


def streak(u):
    cur = r.hgetall(f"streak:{u}")
    return int(cur.get("n", 0)) if cur else 0


def streak_row(u):
    return r.hgetall(f"streak:{u}") or {"last": "", "n": 0}


def users():
    return [int(x) for x in r.smembers("users")]


# --------------------------- PROFIL (bitta pipeline) ---------------------
def profile_stats(u):
    """Profil uchun barcha malumot - 1 ta Redis round trip."""
    p = pair_of(u)
    pipe = r.pipeline()
    pipe.hgetall(f"streak:{u}")
    pipe.get(f"prem:{u}")
    if p:
        pipe.get(f"pts:{p[0]}")
        pipe.get(f"mets:{_pid(u, other(p, u))}")
        pipe.scard(f"mine:{u}")
    rows = pipe.execute()
    st_row = rows[0] or {}
    prem_until = int(rows[1] or 0)
    now = int(dt.datetime.now().timestamp())
    return {
        "pair": p,
        "streak": int(st_row.get("n", 0)) if st_row else 0,
        "prem": bool(prem_until and prem_until >= now),
        "prem_days": max(0, round((prem_until - now) / 86400)) if prem_until > now else 0,
        "pts": int(rows[2] or 0) if p else 0,
        "since": int(rows[3] or 0) if p else 0,
        "letters": int(rows[4] or 0) if p else 0,
    }


# ------------------------------- PREMIUM --------------------------------
def is_prem(u):
    v = r.get(f"prem:{u}")
    return bool(v and int(v) >= int(dt.datetime.now().timestamp()))


def prem_days(u):
    v = r.get(f"prem:{u}")
    if not v:
        return 0
    return max(0, round((int(v) - int(dt.datetime.now().timestamp())) / 86400))


def add_prem(u, days):
    base = dt.datetime.now().timestamp()
    v = r.get(f"prem:{u}")
    if v and int(v) > base:
        base = int(v)
    r.set(f"prem:{u}", int(base + days * 86400))
    r.sadd("prems", u)


# -------------------------------- SOVG'A --------------------------------
def make_gift(days):
    token = secrets.token_urlsafe(8)
    r.hset(f"gift:{token}", mapping={"days": days, "used": 0})
    return token


def use_gift(token, u):
    d = r.hgetall(f"gift:{token}")
    if not d or int(d.get("used", 0)):
        return 0
    r.hset(f"gift:{token}", "used", 1)
    add_prem(u, int(d["days"]))
    return int(d["days"])


# ------------------------------ ESLATMALAR ------------------------------
def sent(u, kind):
    return r.get(f"sent:{u}:{kind}") == today()


def mark(u, kind):
    r.set(f"sent:{u}:{kind}", today())


def reminders_on(u):
    """Foydalanuvchi eslatmalarni o'chirib qo'yganmi (standart — yoqilgan)."""
    return r.get(f"remind:{u}") != "0"


def set_reminders(u, on):
    """on: True/1/"1"/"true"/"on" -> yoqilgan, qolganlari -> o'chirilgan."""
    val = 1 if (on is True or on == 1 or
                (isinstance(on, str) and on.strip().lower() in ("1", "true", "on", "yes"))) else 0
    r.set(f"remind:{u}", val)


# ------------------------------ REFERRAL --------------------------------
REF_BALL = 10                  # har bir taklif uchun juftlikka ball
REF_PREM = {3: 7, 10: 30}      # takliflar soni -> premium kunlari


def set_ref(new, referrer):
    """Yangi foydalanuvchi uchun referrerni bir marta yozadi.

    Faqat botni hali ishlatmagan (streak/xat yo'q) odam "yangi" hisoblanadi —
    eski akkauntlar bilan referral ferma qilib bo'lmaydi.
    """
    try:
        new, referrer = int(new), int(referrer)
    except (TypeError, ValueError):
        return False
    if new == referrer:
        return False
    # faqat hali xat yozmagan odam "yangi" hisoblanadi: botni ochib ko'rgan
    # do'st ham taklif qilina oladi (konversiya uchun), ferma esa yopiq qoladi
    if r.scard(f"mine:{new}") or r.exists(f"ref_done:{new}"):
        return False
    if not r.set(f"ref:{new}", referrer, nx=True):
        return False
    r.incr(f"refs:{referrer}")
    r.incr("cnt:refs")
    return True


def refs(u):
    """Havolani bosganlar (ro'yxatdan o'tganlar)."""
    return int(r.get(f"refs:{u}") or 0)


def refs_ok(u):
    """Birinchi xat yozib, taklifni tasdiqlaganlar."""
    return int(r.get(f"refs_ok:{u}") or 0)


def claim_reward(u):
    """Referral mukofotini atomar qo'llaydi (claim + ball/premium birga).

    Qaytaradi: (referrer, tasdiqlangan_takliflar_soni) yoki None.
    Agar mukofot qo'llanmasa — holat qaytariladi va keyingi xatda qayta uriniladi.
    """
    ref = r.get(f"ref:{u}")
    if not ref:
        return None
    try:
        ref = int(ref)
    except ValueError:
        return None
    if not r.set(f"ref_done:{u}", 1, nx=True):
        return None
    n = int(r.incr(f"refs_ok:{ref}"))
    try:
        apply_ref_reward(ref, n)
    except Exception:  # noqa: BLE001
        try:
            r.delete(f"ref_done:{u}")
            r.decr(f"refs_ok:{ref}")
        except Exception:  # noqa: BLE001
            pass
        return None
    return ref, n


def apply_ref_reward(ref, n):
    """Referrer mukofoti: juftlikka ball + har bosqich uchun bir marta premium."""
    p = pair_of(ref)
    if p:
        add_pts(p[0], REF_BALL)
    if n in REF_PREM and r.set(f"ref_prem:{ref}:{n}", 1, nx=True):
        add_prem(ref, REF_PREM[n])


# -------------------------------- SHIKOYAT -------------------------------
def seen(lid, u):
    """Foydalanuvchi xatni ochganini belgilaydi (shikoyat uchun)."""
    r.sadd(f"seen:{lid}", u)
    r.expire(f"seen:{lid}", 90 * 86400)


def has_seen(lid, u):
    return bool(r.sismember(f"seen:{lid}", u))


def add_report(lid, by, sender, text=""):
    """Bir foydalanuvchi bir xatni faqat bir marta shikoyat qiladi."""
    if not r.set(f"rep:{by}:{lid}", 1, nx=True):
        return False
    r.expire(f"rep:{by}:{lid}", 90 * 86400)
    r.rpush("reports", json.dumps({
        "l": lid, "by": by, "to": sender, "t": str(text)[:200],
        "ts": int(time.time())}))
    r.ltrim("reports", -300, -1)
    return True


def reports(n=10):
    return [json.loads(x) for x in r.lrange("reports", -n, -1)][::-1]


def count_reports():
    return r.llen("reports")


# --------------------------- VAQT KAPSULASI -----------------------------
CAPSULE_MAX_TEXT = 500
CAPSULE_EXPIRE = 3 * 365 * 86400       # havola 3 yil amal qiladi


def add_capsule(sender, text, days, theme="classic"):
    """Kelajakdagi sanaga qulflangan xat. (cid, token, open_at)."""
    cid = r.incr("seq:capsules")
    token = secrets.token_urlsafe(9)
    open_at = int(time.time()) + max(1, int(days)) * 86400
    r.hset(f"capsule:{cid}", mapping={
        "sender": sender, "text": str(text)[:CAPSULE_MAX_TEXT], "theme": theme,
        "open_at": open_at, "ts": int(time.time()), "receiver": "",
        "opened": 0, "notified": 0, "token": token})
    r.set(f"capsule:t:{token}", cid, ex=CAPSULE_EXPIRE)
    r.sadd(f"caps:{sender}", cid)
    r.zadd("caps:due", {str(cid): open_at})
    r.incr(f"cnt:capsules:{today()}")
    return cid, token, open_at


def capsule(cid):
    d = r.hgetall(f"capsule:{cid}")
    if not d or "sender" not in d:
        return None
    return {"id": int(cid), "sender": int(d["sender"]),
            "text": d.get("text", ""), "theme": d.get("theme") or "classic",
            "open_at": int(d.get("open_at") or 0), "ts": int(d.get("ts") or 0),
            "receiver": int(d.get("receiver") or 0),
            "opened": int(d.get("opened") or 0),
            "notified": int(d.get("notified") or 0),
            "token": d.get("token") or ""}


def capsule_by_token(token):
    if not token:
        return None, None
    cid = r.get(f"capsule:t:{token}")
    if not cid:
        return None, None
    return int(cid), capsule(int(cid))


def capsules_of(u):
    rows = []
    for x in r.smembers(f"caps:{u}"):
        c = capsule(int(x))
        if c:
            rows.append(c)
    rows.sort(key=lambda c: c["open_at"])
    return rows


def capsules_today(u):
    start = day_start_ts()
    return sum(1 for c in capsules_of(u) if c["ts"] >= start)


def due_capsules(now_ts=None, limit=200):
    """Vaqti kelgan, hali xabar qilinmagan kapsulalar."""
    now_ts = int(now_ts or time.time())
    out = []
    for cid in r.zrangebyscore("caps:due", "-inf", now_ts, start=0, num=limit):
        c = capsule(int(cid))
        if c:
            out.append(c)
    return out


def open_capsule(cid, u):
    """Kapsulani ochish. Qaytaradi: (capsule | None, sabab).

    sabab: ok / early / none / not_yours
    """
    c = capsule(cid)
    if not c:
        return None, "none"
    if int(time.time()) < c["open_at"]:
        return c, "early"
    if c["receiver"] and u not in (c["receiver"], c["sender"]):
        return None, "not_yours"
    # yuboruvchi o'z xatini ko'radi, lekin qabul qiluvchi o'rnini band qilmaydi
    if u == c["sender"] and c["receiver"] != u:
        return c, "ok"
    r.hset(f"capsule:{cid}", mapping={"receiver": u, "opened": 1})
    r.zrem("caps:due", str(cid))
    c["receiver"], c["opened"] = u, 1
    return c, "ok"


def capsule_notified(cid):
    r.hset(f"capsule:{cid}", "notified", 1)
    r.zrem("caps:due", str(cid))


# ---------------------------- SEVGI BILETLARI ---------------------------
def add_coupon(sender, receiver, title, note=""):
    cid = r.incr("seq:coupons")
    r.hset(f"coupon:{cid}", mapping={
        "from": sender, "to": receiver, "title": str(title)[:60],
        "note": str(note)[:120], "status": "active",
        "ts": int(time.time()), "used_ts": 0})
    r.sadd(f"coupon:from:{sender}", cid)
    r.sadd(f"coupon:to:{receiver}", cid)
    r.incr(f"cnt:coupons:{today()}")
    return cid


def coupon(cid):
    d = r.hgetall(f"coupon:{cid}")
    if not d or "from" not in d:
        return None
    return {"id": int(cid), "from": int(d["from"]), "to": int(d["to"]),
            "title": d.get("title", ""), "note": d.get("note", ""),
            "status": d.get("status") or "active", "ts": int(d.get("ts") or 0),
            "used_ts": int(d.get("used_ts") or 0)}


def coupons_of(u):
    ids = {int(x) for x in r.sunion(f"coupon:from:{u}", f"coupon:to:{u}")}
    rows = [x for x in (coupon(i) for i in ids) if x]
    rows.sort(key=lambda x: x["ts"], reverse=True)
    return rows


def coupons_sent_today(u):
    return sum(1 for x in coupons_of(u)
               if x["from"] == u and x["ts"] >= day_start_ts())


def use_coupon(cid, u):
    """Biletni ishlatish (faqat qabul qiluvchi, bir marta)."""
    with lock(f"coupon:{cid}") as ok:
        if not ok:
            return None, "busy"
        c = coupon(cid)
        if not c:
            return None, "none"
        if c["to"] != u:
            return None, "not_yours"
        if c["status"] != "active":
            return c, "already"
        r.hset(f"coupon:{cid}", mapping={"status": "used",
                                         "used_ts": int(time.time())})
        c["status"], c["used_ts"] = "used", int(time.time())
        return c, "ok"


# ------------------------------- ADMIN ----------------------------------
def admin_stats():
    t = today()
    prem_all = []
    for x in r.smembers("prems"):
        try:
            prem_all.append(int(x))
        except (TypeError, ValueError):
            continue
    prem_active = 0
    if prem_all:
        nowts = int(dt.datetime.now().timestamp())
        pipe = r.pipeline()
        for u in prem_all:
            pipe.get(f"prem:{u}")
        for v in pipe.execute():
            try:
                if v and int(v) >= nowts:
                    prem_active += 1
            except (TypeError, ValueError):
                continue
    return {"users": r.scard("users"),
            "pairs": int(r.get("cnt:pairs") or 0),
            "letters": int(r.get("seq:letters") or 0),
            "prem": len(prem_all),
            "prem_active": prem_active,
            "active_today": r.scard(f"active:{t}"),
            "new_today": r.scard(f"new:{t}"),
            "letters_today": int(r.get(f"cnt:letters:{t}") or 0),
            "pairs_today": int(r.get(f"cnt:pairs:{t}") or 0),
            "refs": int(r.get("cnt:refs") or 0),
            "capsules": int(r.get("seq:capsules") or 0),
            "coupons": int(r.get("seq:coupons") or 0),
            "reports": r.llen("reports"),
            "feedback": r.llen("feedback")}
