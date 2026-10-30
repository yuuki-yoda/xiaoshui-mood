#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小水的心情系统 —— 灵感来自「大肥鱼」的 dsh-feiyu-mood。

每轮聊完由小水自己判断涨跌，调 apply 记账；数值随时间自然往 baseline 漂。
用法:
  mood.py apply -d 3 -r "雪老师夸我了" [-t warm]
  mood.py status
  mood.py history -n 20
  mood.py reset
  mood.py json          # 给网页挂饰用
"""
import argparse
import json
import math
import os
import sys
import time

HOME = os.path.expanduser("~")
STATE_PATH = os.path.join(HOME, ".openclaw", "workspace", "memory", "mood", "state.json")
MAX_EVENTS = 400
BASELINE = 62.0
DECAY_PER_HOUR = 0.8          # 每小时往 baseline 漂多少
SPAN = 0.0                    # 数值 0-100 硬边界

LEVELS = [
    (0, "乌云压顶", "🌧", "#5b6b8c"),
    (20, "有点闷", "🌫", "#7a7f96"),
    (40, "平静", "🌙", "#8fa3bf"),
    (60, "还不错", "🌤", "#7fc4a7"),
    (80, "元气满满", "🌟", "#f2a65a"),
]


def _default():
    now = time.time()
    return {
        "value": BASELINE,
        "baseline": BASELINE,
        "created": now,
        "updated": now,
        "events": [],
    }


def load():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        st = _default()
    # 兼容缺字段
    d = _default()
    for k, v in d.items():
        st.setdefault(k, v)
    return st


def save(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def apply_decay(st, now=None):
    now = now or time.time()
    last = float(st.get("updated") or now)
    hours = max(0.0, (now - last) / 3600.0)
    if hours <= 0:
        return st
    base = float(st.get("baseline", BASELINE))
    val = float(st.get("value", base))
    # 指数回归，半衰期 ~ 6h
    k = DECAY_PER_HOUR / 6.0
    val = base + (val - base) * math.exp(-k * hours)
    st["value"] = max(0.0, min(100.0, val))
    st["updated"] = now
    return st


def level_of(value):
    label, emoji, color = LEVELS[0][1], LEVELS[0][2], LEVELS[0][3]
    for lo, lb, em, co in LEVELS:
        if value >= lo:
            label, emoji, color = lb, em, co
    return label, emoji, color


def do_apply(delta, reason, tag=""):
    st = load()
    st = apply_decay(st)
    before = st["value"]
    after = max(0.0, min(100.0, before + float(delta)))
    st["value"] = after
    st["updated"] = time.time()
    ev = {
        "ts": int(st["updated"]),
        "delta": round(float(delta), 2),
        "before": round(before, 1),
        "after": round(after, 1),
        "reason": (reason or "").strip()[:120],
        "tag": tag or "",
    }
    st.setdefault("events", []).append(ev)
    if len(st["events"]) > MAX_EVENTS:
        st["events"] = st["events"][-MAX_EVENTS:]
    save(st)
    return st, ev


def do_status(st=None):
    st = apply_decay(load())
    save(st)
    v = st["value"]
    label, emoji, _ = level_of(v)
    print("%s %s  %.1f/100  (baseline %.0f)" % (emoji, label, v, st.get("baseline", BASELINE)))
    evs = st.get("events") or []
    if evs:
        print("最近 %d 条:" % min(5, len(evs)))
        for e in evs[-5:]:
            t = time.strftime("%m-%d %H:%M", time.localtime(e["ts"]))
            sign = "+" if e["delta"] >= 0 else ""
            print("  %s  %s%.1f → %.1f  %s" % (t, sign, e["delta"], e["after"], e["reason"]))
    return st


def do_history(n=20):
    st = load()
    evs = (st.get("events") or [])[-n:]
    for e in evs:
        t = time.strftime("%m-%d %H:%M", time.localtime(e["ts"]))
        sign = "+" if e["delta"] >= 0 else ""
        print("%s  %s%.1f  %.1f→%.1f  [%s] %s" % (t, sign, e["delta"], e["before"], e["after"], e.get("tag", ""), e["reason"]))


def do_json():
    st = load()
    st = apply_decay(st)
    save(st)
    v = st["value"]
    label, emoji, color = level_of(v)
    # 24h 走势：按小时聚合
    now = time.time()
    buckets = []
    for i in range(23, -1, -1):
        start = now - (i + 1) * 3600
        end = now - i * 3600
        pts = [e["after"] for e in st.get("events", []) if start <= e["ts"] < end]
        buckets.append({"hour": time.strftime("%H:%M", time.localtime(end)), "value": round(sum(pts) / len(pts), 1) if pts else None})
    out = {
        "value": round(v, 1),
        "label": label,
        "emoji": emoji,
        "color": color,
        "baseline": st.get("baseline", BASELINE),
        "updated": int(now),
        "events": [
            {
                "ts": e["ts"],
                "time": time.strftime("%m-%d %H:%M", time.localtime(e["ts"])),
                "delta": e["delta"],
                "after": e["after"],
                "reason": e["reason"],
                "tag": e.get("tag", ""),
            }
            for e in (st.get("events") or [])[-30:][::-1]
        ],
        "hours": buckets,
    }
    print(json.dumps(out, ensure_ascii=False))


def do_reset():
    st = _default()
    save(st)
    print("心情重置为 %.0f" % BASELINE)


def main():
    ap = argparse.ArgumentParser(description="小水的心情系统")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("apply")
    a.add_argument("-d", "--delta", type=float, required=True)
    a.add_argument("-r", "--reason", default="")
    a.add_argument("-t", "--tag", default="")
    s = sub.add_parser("status")
    h = sub.add_parser("history")
    h.add_argument("-n", type=int, default=20)
    sub.add_parser("json")
    sub.add_parser("reset")
    args = ap.parse_args()

    if args.cmd == "apply":
        st, ev = do_apply(args.delta, args.reason, args.tag)
        label, emoji, _ = level_of(st["value"])
        sign = "+" if ev["delta"] >= 0 else ""
        print("%s %s %.1f (%s%.1f) — %s" % (emoji, label, ev["after"], sign, ev["delta"], ev["reason"]))
    elif args.cmd == "history":
        do_history(args.n)
    elif args.cmd == "json":
        do_json()
    elif args.cmd == "reset":
        do_reset()
    else:
        do_status()


if __name__ == "__main__":
    main()
