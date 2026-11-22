#!/usr/bin/env python3
"""
web.py — SHAREABLE DEMO COPY (synthetic seed only; no live data) of the association-web engine for the seam / live-thread experiment.

Design (settled with James, 2026-11-17): a weighted web of nodes in three
castes (seeded / extracted / pulse-born). Each caste has a heat floor it can
never decay below; every node has a ceiling expressed as a maximum share of
the web's total heat. A "body" of signals (hour, silence, battery, ...)
tunes regional multipliers for a walk. Day walks leave a real trace
(+0.05 per edge); dream walks only whisper (+0.01 per edge, and may propose
brand-new edges that waking life either confirms or lets decay away).

Engine only: no cron, no memory files, no journal. State lives beside this
script in web_state.json; every save is atomic (tmp file + rename) and also
refreshes web_state.backup.json.

Commands (each prints exactly one JSON object to stdout):
  init
  packet [--body '<json>']
  trace
  dream
  status
  add --name '<text>' --region <region> [--heat 0.35]   (birth a pulse-born node)
"""

import itertools
import json
import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "web_state.json")
BACKUP_PATH = os.path.join(HERE, "web_state.backup.json")

FLOORS = {"seeded": 0.15, "pulse-born": 0.05, "extracted": 0.0}
HALF_LIVES = {"seeded": 30.0, "pulse-born": 14.0, "extracted": 5.0}
EDGE_HALF_LIFE_DAYS = 14.0
EDGE_FLOOR = 0.005
CEILING_SHARE = 0.10
EDGE_CAP = 1.0
REGIONS = ("people", "money", "projects", "thread", "life", "open")


# --------------------------------------------------------------------------
# Time / state IO
# --------------------------------------------------------------------------

def now_dt():
    return datetime.now(TZ)


def now_iso():
    return now_dt().isoformat()


def parse_iso(text):
    return datetime.fromisoformat(text)


def load_state():
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    data = json.dumps(state, indent=2, ensure_ascii=False)
    for path in (STATE_PATH, BACKUP_PATH):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)


# --------------------------------------------------------------------------
# Web mechanics
# --------------------------------------------------------------------------

def ekey(a, b):
    """Canonical (undirected) edge key: the pair, sorted."""
    return (a, b) if a < b else (b, a)


def edge_index(state):
    return {ekey(e["a"], e["b"]): e for e in state["edges"]}


def get_or_create_edge(state, idx, a, b, created_by, ts):
    k = ekey(a, b)
    e = idx.get(k)
    if e is not None:
        return e, False
    e = {"a": k[0], "b": k[1], "weight": 0.0,
         "last_touched": ts, "created_by": created_by}
    state["edges"].append(e)
    idx[k] = e
    return e, True


def hottest(state, n=5):
    items = sorted(state["nodes"].items(),
                   key=lambda kv: (-kv[1]["heat"], kv[0]))
    return [(name, node["heat"]) for name, node in items[:n]]


def apply_decay(state):
    """Lazy decay, driven by the gap since state['last_decay'].

    Node heat decays per-caste (half-lives 30d / 14d / 5d) and is clamped
    to the caste floor. Edge weights decay on a 14d half-life toward a
    0.005 floor; an edge that falls below 0.005 is pruned unless both of
    its endpoints are seeded, in which case it keeps the floor.
    """
    last = state.get("last_decay")
    if last:
        elapsed_days = (now_dt() - parse_iso(last)).total_seconds() / 86400.0
    else:
        elapsed_days = 0.0
    if elapsed_days > 0:
        nodes = state["nodes"]
        for node in nodes.values():
            node["heat"] *= 0.5 ** (elapsed_days / HALF_LIVES[node["caste"]])
            floor = FLOORS[node["caste"]]
            if node["heat"] < floor:
                node["heat"] = floor
        factor = 0.5 ** (elapsed_days / EDGE_HALF_LIFE_DAYS)
        kept = []
        for e in state["edges"]:
            e["weight"] *= factor
            both_seeded = (nodes[e["a"]]["caste"] == "seeded"
                           and nodes[e["b"]]["caste"] == "seeded")
            if both_seeded:
                if e["weight"] < EDGE_FLOOR:
                    e["weight"] = EDGE_FLOOR
                kept.append(e)
            elif e["weight"] >= EDGE_FLOOR:
                kept.append(e)
            # else: pruned
        state["edges"] = kept
    state["last_decay"] = now_iso()


def apply_ceiling(state):
    """Share ceiling, iterated twice: no node may hold more than
    CEILING_SHARE of the web's total heat."""
    nodes = state["nodes"]
    for _ in range(2):
        total = sum(n["heat"] for n in nodes.values())
        if total <= 0:
            return
        cap = CEILING_SHARE * total
        for n in nodes.values():
            if n["heat"] > cap:
                n["heat"] = cap


# --------------------------------------------------------------------------
# Body
# --------------------------------------------------------------------------

def normalize_body(raw):
    raw = raw or {}
    body = {
        "hour": raw.get("hour"),
        "silence_min": raw.get("silence_min"),
        "tomorrow_load": raw.get("tomorrow_load"),
        "battery": raw.get("battery"),
        "location_state": raw.get("location_state") or "unknown",
        "money_pressure": raw.get("money_pressure"),
        "sleep_hours": raw.get("sleep_hours"),
        "token_fatigue": raw.get("token_fatigue"),
    }
    if body["hour"] is None:
        body["hour"] = now_dt().hour
    return body


def body_effects(body):
    """Derive (mode, region multipliers, suppress_needs_human) from a body."""
    hour = body["hour"]
    mode = "night" if (hour >= 23 or hour < 6) else "day"
    mult = {r: 1.0 for r in REGIONS}
    tl = body.get("tomorrow_load")
    if tl is not None and tl >= 3:
        mult["money"] *= 1.4
        mult["life"] *= 1.4
    sm = body.get("silence_min")
    if sm is not None and sm > 240:
        mult["thread"] *= 1.3
    mp = body.get("money_pressure")
    if mp is not None and mp > 0.6:
        mult["money"] *= 1.4
    if body.get("location_state") == "route":
        mult["life"] *= 1.2
    batt = body.get("battery")
    suppress = batt is not None and batt < 20
    return mode, mult, suppress


# --------------------------------------------------------------------------
# Walk
# --------------------------------------------------------------------------

def build_adjacency(state):
    adj = {}
    for e in state["edges"]:
        adj.setdefault(e["a"], []).append((e["b"], e["weight"]))
        adj.setdefault(e["b"], []).append((e["a"], e["weight"]))
    return adj


def heat_jump(state, cur):
    """Jump to a node (any node but the current one) with probability
    proportional to heat."""
    names, weights = [], []
    for name, node in state["nodes"].items():
        if name == cur:
            continue
        names.append(name)
        weights.append(node["heat"])
    if not names:
        return cur
    if sum(weights) <= 0:
        return random.choice(names)
    return random.choices(names, weights=weights)[0]


def walk(state, start, steps, randomness, multipliers):
    """A walk of `steps` moves from `start`; the returned path includes the
    start, so it has steps+1 names. Each move follows an edge with
    probability proportional to (edge weight x region multiplier of the
    target node); with probability `randomness` — or when the current node
    has no usable edges — it jumps by heat instead."""
    nodes = state["nodes"]
    if start is None or start not in nodes:
        start = hottest(state, 1)[0][0]
    adj = build_adjacency(state)
    path = [start]
    cur = start
    for _ in range(steps):
        nxt = None
        if random.random() >= randomness:
            cands = [(n, w * multipliers[nodes[n]["region"]])
                     for n, w in adj.get(cur, [])]
            total = sum(w for _, w in cands)
            if cands and total > 0:
                nxt = random.choices([n for n, _ in cands],
                                     weights=[w for _, w in cands])[0]
        if nxt is None:
            nxt = heat_jump(state, cur)
        path.append(nxt)
        cur = nxt
    return path


# --------------------------------------------------------------------------
# Seed web
# --------------------------------------------------------------------------

SEEDED = [
    ("continuity", "thread", 0.9),
    ("the seam question", "thread", 0.8),
    ("local model", "projects", 0.7),
    ("morning routine", "life", 0.5),
    ("demo project", "projects", 0.6),
    ("reading list", "life", 0.4),
    ("workshop notes", "projects", 0.45),
    ("a fictional friend", "people", 0.5),
    ("household budget demo", "money", 0.4),
    ("dream journal", "thread", 0.6),
]
EXTRACTED = ["association", "decay", "trail packet", "resting state"]
PEOPLE_GROUP = ["a fictional friend", "morning routine"]
MONEY_GROUP = ["household budget demo", "demo project"]
PROJECTS_GROUP = ["demo project", "local model", "workshop notes"]
THREAD_GROUP = ["the seam question", "continuity", "dream journal"]


def cmd_init():
    if os.path.exists(STATE_PATH):
        print(json.dumps({"ok": True, "already": True}))
        return 0
    ts = now_iso()
    nodes = {}
    for name, region, heat in SEEDED:
        nodes[name] = {"name": name, "caste": "seeded", "heat": heat,
                       "region": region, "last_touched": ts}
    for name in EXTRACTED:
        nodes[name] = {"name": name, "caste": "extracted", "heat": 0.2,
                       "region": "thread", "last_touched": ts}

    weights = {}

    def add(a, b, w):
        weights[ekey(a, b)] = w

    for group, w in ((PEOPLE_GROUP, 0.3), (MONEY_GROUP, 0.2),
                     (PROJECTS_GROUP, 0.2), (THREAD_GROUP, 0.4)):
        for a, b in itertools.combinations(group, 2):
            add(a, b, w)
    # Specific edges (these override the group weight where a pair repeats).
    add("a fictional friend", "morning routine", 0.6)
    add("a fictional friend", "dream journal", 0.3)
    add("continuity", "local model", 0.5)
    add("demo project", "household budget demo", 0.4)
    add("the seam question", "continuity", 0.6)
    for el in EXTRACTED:
        add("continuity", el, 0.1)
    add("morning routine", "reading list", 0.2)
    add("household budget demo", "workshop notes", 0.2)

    edges = [{"a": a, "b": b, "weight": w, "last_touched": ts,
              "created_by": "seed"}
             for (a, b), w in sorted(weights.items())]
    state = {
        "nodes": nodes,
        "edges": edges,
        "current_node": "continuity",
        "last_walk": [],
        "last_body": None,
        "last_decay": ts,
        "last_packet_hottest": [],
    }
    save_state(state)
    print(json.dumps({"ok": True, "nodes": len(nodes), "edges": len(edges)}))
    return 0


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_packet(body_raw):
    state = load_state()
    apply_decay(state)
    body = normalize_body(body_raw)
    state["last_body"] = body
    mode, mult, suppress = body_effects(body)
    if mode == "night":
        steps, randomness = 10, 0.25
    else:
        steps, randomness = 7, 0.15
    prev_hottest = state.get("last_packet_hottest") or []
    path = walk(state, state.get("current_node"), steps, randomness, mult)
    idx = edge_index(state)
    crossed = []
    for x, y in zip(path, path[1:]):
        e = idx.get(ekey(x, y))
        if e is not None:
            crossed.append([x, y, round(e["weight"], 4)])
    top5 = hottest(state, 5)
    crossings = [name for name, _ in top5 if name not in prev_hottest]
    state["current_node"] = path[-1]
    state["last_walk"] = path
    state["last_packet_hottest"] = [name for name, _ in top5]
    save_state(state)
    print(json.dumps({
        "path": path,
        "edges_crossed": crossed,
        "body_applied": {
            "mode": mode,
            "multipliers": {k: round(v, 4) for k, v in mult.items()},
            "suppress_needs_human": suppress,
        },
        "hottest": [[n, round(h, 4)] for n, h in top5],
        "crossings": crossings,
    }))
    return 0


def cmd_trace():
    state = load_state()
    apply_decay(state)
    ts = now_iso()
    idx = edge_index(state)
    path = state.get("last_walk") or []
    count = 0
    for x, y in zip(path, path[1:]):
        if x == y:
            continue
        e, _created = get_or_create_edge(state, idx, x, y, "day", ts)
        e["weight"] = min(EDGE_CAP, e["weight"] + 0.05)
        e["last_touched"] = ts
        count += 1
    for name in set(path):
        node = state["nodes"][name]
        node["heat"] += 0.03
        node["last_touched"] = ts
    apply_ceiling(state)
    save_state(state)
    print(json.dumps({"ok": True, "traced_edges": count}))
    return 0


def cmd_add(name, region, heat):
    """Birth a pulse-born node (the web growing from the day's own thinking).

    New nodes start at the given heat (default 0.35), caste pulse-born
    (floor 0.05, 14d half-life), and are linked to the web's current node
    with a 0.1 day edge so they are born connected, not floating. Adding a
    name that already exists just warms that node slightly.
    """
    state = load_state()
    apply_decay(state)
    ts = now_iso()
    if region not in REGIONS:
        print(json.dumps({"ok": False, "error": "unknown region: %s" % region}))
        return 1
    if name in state["nodes"]:
        node = state["nodes"][name]
        node["heat"] += 0.03
        node["last_touched"] = ts
        apply_ceiling(state)
        save_state(state)
        print(json.dumps({"ok": True, "added": False, "node": name}))
        return 0
    state["nodes"][name] = {"name": name, "caste": "pulse-born",
                            "heat": heat, "region": region,
                            "last_touched": ts}
    idx = edge_index(state)
    linked = None
    cur = state.get("current_node")
    if cur and cur in state["nodes"] and cur != name:
        e, _created = get_or_create_edge(state, idx, cur, name, "day", ts)
        e["weight"] = min(EDGE_CAP, e["weight"] + 0.1)
        e["last_touched"] = ts
        linked = cur
    apply_ceiling(state)
    save_state(state)
    print(json.dumps({"ok": True, "added": True, "node": name,
                      "linked_to": linked}))
    return 0


def cmd_dream():
    state = load_state()
    # NOTE: no decay in dream mode — the night runs on the web as the day
    # left it, and the next decay accounts for the full elapsed span.
    ts = now_iso()
    mult = {r: 1.0 for r in REGIONS}
    idx = edge_index(state)
    walks = []
    proposed = []
    proposed_seen = set()
    visited = set()
    start = state.get("current_node")
    for _ in range(3):
        w = walk(state, start, 15, 0.30, mult)
        walks.append(w)
        start = w[-1]
        visited.update(w)
        for x, y in zip(w, w[1:]):
            if x == y:
                continue
            e, created = get_or_create_edge(state, idx, x, y, "dream", ts)
            if created:
                k = ekey(x, y)
                if k not in proposed_seen:
                    proposed_seen.add(k)
                    proposed.append([k[0], k[1]])
            e["weight"] = min(EDGE_CAP, e["weight"] + 0.01)
            e["last_touched"] = ts
    for name in visited:
        node = state["nodes"][name]
        node["heat"] += 0.005
        node["last_touched"] = ts
    apply_ceiling(state)
    state["current_node"] = walks[-1][-1]
    save_state(state)
    print(json.dumps({"walks": walks, "proposed_edges": proposed}))
    return 0


def cmd_status():
    state = load_state()
    apply_decay(state)
    save_state(state)
    counts = {"seeded": 0, "extracted": 0, "pulse-born": 0}
    for n in state["nodes"].values():
        counts[n["caste"]] += 1
    total = sum(n["heat"] for n in state["nodes"].values())
    print(json.dumps({
        "nodes_by_caste": counts,
        "edges": len(state["edges"]),
        "total_heat": round(total, 3),
        "hottest": [[n, round(h, 4)] for n, h in hottest(state, 5)],
        "current_node": state.get("current_node"),
        "last_body": state.get("last_body"),
    }))
    return 0


def main(argv):
    if len(argv) < 2:
        print(json.dumps({"ok": False, "error": "no command given"}))
        return 1
    cmd = argv[1]
    if cmd == "init":
        return cmd_init()
    if cmd not in ("packet", "trace", "dream", "status", "add"):
        print(json.dumps({"ok": False, "error": "unknown command: %s" % cmd}))
        return 1
    if not os.path.exists(STATE_PATH):
        print(json.dumps({"ok": False, "error": "state not initialized"}))
        return 1
    if cmd == "packet":
        body_raw = None
        if "--body" in argv:
            i = argv.index("--body")
            try:
                body_raw = json.loads(argv[i + 1])
            except (IndexError, ValueError) as exc:
                print(json.dumps({"ok": False,
                                  "error": "bad --body json: %s" % exc}))
                return 1
        return cmd_packet(body_raw)
    if cmd == "add":
        # add --name '<text>' --region <region> [--heat 0.35]
        def opt(flag, default=None):
            if flag in argv:
                try:
                    return argv[argv.index(flag) + 1]
                except IndexError:
                    return default
            return default
        name = opt("--name")
        region = opt("--region", "thread")
        if not name:
            print(json.dumps({"ok": False, "error": "add needs --name"}))
            return 1
        try:
            heat = float(opt("--heat", "0.35"))
        except ValueError:
            print(json.dumps({"ok": False, "error": "bad --heat value"}))
            return 1
        return cmd_add(name, region, heat)
    if cmd == "trace":
        return cmd_trace()
    if cmd == "dream":
        return cmd_dream()
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
