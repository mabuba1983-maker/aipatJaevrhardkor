# -*- coding: utf-8 -*-
"""Self-made practice: the mind invents random programs from what it already owns, hides the program, and tries to rediscover it from examples alone.
Problems it can only solve with a BIG search become skills (so next time they are one step). It never needs a teacher, so it never runs out of lessons."""
import hashlib, random
from .synth import evaluate, size, type_of, INT, LIST, STR, SLIST, _tup
from .verify import fuzz_inputs
from . import curriculum as cur

def _gen(table, by_ret, rng, t, depth, in_t):
    if depth == 0 or rng.random() < 0.15:
        return ("x",) if t == in_t else None
    ops = by_ret.get(t, [])
    if not ops: return ("x",) if t == in_t else None
    for _ in range(8):
        name = rng.choice(ops); kids = [_gen(table, by_ret, rng, a, depth - 1, in_t) for a in table[name][0]]
        if all(k is not None for k in kids): return (name,) + tuple(kids)
    return None

def run(m, tries=40, keep=4, seed=0, max_seconds=240, say=print):
    import time
    from .mind import Mind
    rng = random.Random(seed + m.state.get("sp", 0)); m.state["sp"] = m.state.get("sp", 0) + 1; table = m.lib.table(); t0 = time.time(); added = []
    by_ret = {}
    for name, (atypes, rt, _, _) in table.items():
        if len(atypes) == 1 and "op:" not in name: by_ret.setdefault(rt, []).append(name)
    auto = [s for s in m.lib.skills if s.startswith("auto_")]
    for _ in range(tries):
        if len(added) >= keep or len(auto) + len(added) >= 60 or time.time() - t0 > max_seconds: break
        in_t = rng.choice([LIST, LIST, STR, INT]); out_t = rng.choice([INT, INT, LIST, BOOL_OR(STR)])
        e = _gen(table, by_ret, rng, out_t, rng.randint(3, 4), in_t)
        if e is None or size(e) < 4: continue
        ins = fuzz_inputs(in_t, rng.randint(1, 10 ** 6), 14); outs = [evaluate(e, (i,), m.lib, table) for i in ins]
        if any(o is None for o in outs) or len({repr(o) for o in outs}) < 4: continue
        pairs = [[i, o] for i, o in zip(ins, outs)]
        tid = "auto_" + hashlib.sha1(repr(e).encode()).hexdigest()[:8]
        if tid in m.lib.skills or any(s["expr"] == e for s in m.lib.skills.values()): continue
        from .synth import solve
        cheap, _ = solve(pairs[:7], pairs[7:], m.lib, cur.EXAM_SIZE, cur.EXAM_NODES, 10)
        if cheap is not None: continue                                   # already easy for it: nothing to learn
        task = {"id": tid, "level": 8, "desc_ar": "تمرين ذاتي: " + _name(e), "desc_en": "self practice: " + _name(e), "examples": pairs[:7], "holdout": pairs[7:]}
        ok, info = m.learn_task(task, 7, 600000, 40)
        if ok: added.append(tid); say(f"selfplay: learned {tid} ({_name(e)})")
    return added

def BOOL_OR(t): return t
def _name(e): return e[0].replace("skill:", "") if e[0] in ("x",) else (e[0].replace("skill:", "") + "(" + ", ".join(_name(c) for c in e[1:] if c[0] not in ("c",)) + ")") if e[0] != "x" else "x"
