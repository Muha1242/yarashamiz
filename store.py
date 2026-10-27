"""Yarashamiz v3.2 — Redis Ma'lumotlar Qatlami.
"""
import datetime as dt
import json
import os
import time
import redis

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
today = lambda: dt.date.today().isoformat()

def _pid(a, b):
    return f"{min(a, b)}:{max(a, b)}"

def pair_of(u):
    m = r.get(f"mate:{u}")
    if not m:
        return None
    o = int(m)
    return (_pid(u, o), u, o)

def other(p, u):
    return p[2] if p[1] == u else p[1]

# --- Vaqt Kapsulasi (Time Capsule) ---
def add_capsule(sender, receiver, text, theme, unlock_date):
    cid = r.incr("seq:capsules")
    r.hset(f"capsule:{cid}", mapping={
        "sender": sender, "receiver": receiver, "text": text,
        "theme": theme, "ts": int(time.time()), "unlock_date": unlock_date, "opened": 0
    })
    r.sadd(f"capsules:{sender}", cid)
    r.sadd(f"capsules:{receiver}", cid)
    return cid

def get_my_capsules(u):
    cids = r.smembers(f"capsules:{u}")
    res = []
    t = today()
    for cid in cids:
        d = r.hgetall(f"capsule:{cid}")
        if d:
            is_locked = d["unlock_date"] > t and int(d["sender"]) != u
            res.append({
                "id": cid,
                "sender": int(d["sender"]),
                "text": "🔒 Vaqt kapsulasi hali yopiq" if is_locked else d["text"],
                "unlock_date": d["unlock_date"],
                "locked": is_locked,
                "mine": int(d["sender"]) == u
            })
    return res

# --- Sevgi Biletlari (Love Coupons) ---
def add_coupon(sender, receiver, title, desc):
    cpid = r.incr("seq:coupons")
    r.hset(f"coupon:{cpid}", mapping={
        "sender": sender, "receiver": receiver, "title": title,
        "desc": desc, "used": 0, "ts": int(time.time())
    })
    r.sadd(f"coupons:{receiver}", cpid)
    return cpid

def use_coupon(cpid, u):
    d = r.hgetall(f"coupon:{cpid}")
    if not d or int(d["receiver"]) != u or int(d["used"]) != 0:
        return False
    r.hset(f"coupon:{cpid}", "used", 1)
    return True

def get_my_coupons(u):
    cpids = r.smembers(f"coupons:{u}")
    res = []
    for cpid in cpids:
        d = r.hgetall(f"coupon:{cpid}")
        if d:
            res.append({
                "id": cpid, "title": d["title"], "desc": d["desc"],
                "used": int(d["used"]), "sender": int(d["sender"])
            })
    return res

def is_prem(u):
    v = r.get(f"prem:{u}")
    return bool(v and int(v) >= int(dt.datetime.now().timestamp()))
