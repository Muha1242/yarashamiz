"""Yarashamiz v3 (Vercel/webhook) — ma'lumotlar qatlami: Upstash Redis.

Serverless muhitda SQLite ishlamaydi (fayl tizimi vaqtinchalik), shuning uchun
barcha ma'lumotlar Redis'da saqlanadi. Barcha funksiyalar sinkron — polling
rejimidan farqi yo'q.
Talab: REDIS_URL muhit o'zgaruvchisi (Upstash → "Redis" → "TCP endpoint").
"""
import datetime as dt
import json
import os
import time

import redis

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
today = lambda: dt.date.today().isoformat()

GAMES = {
    "ab": {"name": "A yoki B", "n": 5, "mode": "guess"},
    "wh": {"name": "Kim ko'proq?", "n": 5, "mode": "match"},
    "ms": {"name": "Kunlik missiya", "n": 1, "mode": "mission"},
    "qz": {"name": "Sevgi kvizi", "n": 6, "mode": "match", "prem": True},
}


def _pid(a, b):
    return f"{min(a, b)}:{max(a, b)}"


# ------------------------------- JUFTLIK --------------------------------
def pair_of(u):
    """(pid, a, b) yoki None — eski sqlite versiyasi bilan bir xil shakl."""
    m = r.get(f"mate:{u}")
    if not m:
        return None
    o = int(m)
    pid = _pid(u, o)
    return (pid, u, o)


def other(p, u):
    return p[2] if p[1] == u else p[1]


def add_pair(a, b):
    r.set(f"mate:{a}", b)
    r.set(f"mate:{b}", a)
    r.set(f"mets:{_pid(a, b)}", int(time.time()))


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
        "theme": theme, "ts": int(time.time()), "receiver": ""})
    r.sadd(f"mine:{sender}", lid)
    return lid


def letter(lid):
    d = r.hgetall(f"letter:{lid}")
    if not d:
        return None
    return {"id": int(lid), "sender": int(d["sender"]), "text": d["text"],
            "offers": json.loads(d["offers"]), "theme": d["theme"],
            "ts": int(d["ts"]), "receiver": int(d["receiver"] or 0)}


def set_receiver(lid, u):
    r.hset(f"letter:{lid}", "receiver", u)
    r.sadd(f"got:{u}", lid)


def count_today_letters(u, since_ts):
    ids = [int(x) for x in r.smembers(f"mine:{u}")]
    return sum(1 for i in ids if letter(i)["ts"] > since_ts)


def count_letters(u):
    return r.scard(f"mine:{u}")


def my_library(u, limit=20):
    ids = [int(x) for x in r.sunion(f"mine:{u}", f"got:{u}")]
    rows = [letter(i) for i in ids]
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


# ------------------------------- SERIYA ---------------------------------
def touch(u):
    t, cur = today(), r.hgetall(f"streak:{u}")
    if not cur:
        n = 1
        r.hset(f"streak:{u}", mapping={"last": t, "n": 1})
    elif cur["last"] == t:
        n = int(cur["n"])
    else:
        y = (dt.date.today() - dt.timedelta(1)).isoformat()
        n = int(cur["n"]) + 1 if cur["last"] == y else 1
        r.hset(f"streak:{u}", mapping={"last": t, "n": n})
    r.sadd("users", u)
    return n


def streak(u):
    cur = r.hgetall(f"streak:{u}")
    return int(cur.get("n", 0)) if cur else 0


def streak_row(u):
    return r.hgetall(f"streak:{u}") or {"last": "", "n": 0}


def users():
    return [int(x) for x in r.smembers("users")]


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


# -------------------------------- SOVG'A --------------------------------
def make_gift(days):
    import secrets
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
