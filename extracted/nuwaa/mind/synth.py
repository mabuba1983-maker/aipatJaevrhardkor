# -*- coding: utf-8 -*-
"""Program synthesis: the mind WRITES small functions from input/output examples by searching expression trees (smallest first).
Skills it already learned become new building blocks, so later programs are found faster (library learning).
Programs are stored as DATA (expression trees), rendered to Python source, and verified in a separate process."""
import time

INT, BOOL, LIST, STR, SLIST = "int", "bool", "list", "str", "slist"
def _ok(v):
    if v is None: return False
    if isinstance(v, bool): return True
    if isinstance(v, int): return abs(v) <= 10 ** 9
    if isinstance(v, (list, str)): return len(v) <= 200 and (not isinstance(v, list) or all(_ok(i) for i in v))
    return False
def _tup(v): return tuple(v) if isinstance(v, list) else v
def _safe(f):
    def g(*a):
        try:
            r = f(*a); return r if _ok(r) else None
        except Exception: return None
    return g

# name: (arg types, result type, function, python template)
OPS = {}
def op(name, args, ret, fn, py): OPS[name] = (tuple(args), ret, _safe(fn), py)
for n, f, p in [("add", lambda a, b: a + b, "({0} + {1})"), ("sub", lambda a, b: a - b, "({0} - {1})"), ("mul", lambda a, b: a * b, "({0} * {1})"),
                ("fdiv", lambda a, b: a // b, "({0} // {1})"), ("mod", lambda a, b: a % b, "({0} % {1})"), ("max2", max, "max({0}, {1})"), ("min2", min, "min({0}, {1})")]:
    op(n, [INT, INT], INT, f, p)
op("neg", [INT], INT, lambda a: -a, "(-{0})"); op("abs", [INT], INT, abs, "abs({0})")
for n, f, p in [("eq_i", lambda a, b: a == b, "({0} == {1})"), ("gt", lambda a, b: a > b, "({0} > {1})"), ("lt", lambda a, b: a < b, "({0} < {1})")]: op(n, [INT, INT], BOOL, f, p)
op("eq_l", [LIST, LIST], BOOL, lambda a, b: a == b, "({0} == {1})"); op("eq_s", [STR, STR], BOOL, lambda a, b: a == b, "({0} == {1})")
op("not", [BOOL], BOOL, lambda a: not a, "(not {0})"); op("and", [BOOL, BOOL], BOOL, lambda a, b: a and b, "({0} and {1})")
op("is_even", [INT], BOOL, lambda a: a % 2 == 0, "({0} % 2 == 0)")
for t in (INT, STR): op("if_" + t, [BOOL, t, t], t, lambda c, a, b: a if c else b, "({1} if {0} else {2})")
for t, nm in ((LIST, "list"), (SLIST, "slist")):
    op("len_" + nm, [t], INT, len, "len({0})"); op("rev_" + nm, [t], t, lambda a: a[::-1], "{0}[::-1]"); op("sorted_" + nm, [t], t, sorted, "sorted({0})")
    op("tail_" + nm, [t], t, lambda a: a[1:], "{0}[1:]"); op("init_" + nm, [t], t, lambda a: a[:-1], "{0}[:-1]")
    op("uniq_" + nm, [t], t, lambda a: list(dict.fromkeys(a)), "list(dict.fromkeys({0}))")
op("sum", [LIST], INT, sum, "sum({0})"); op("max", [LIST], INT, max, "max({0})"); op("min", [LIST], INT, min, "min({0})")
op("first", [LIST], INT, lambda a: a[0], "{0}[0]"); op("last", [LIST], INT, lambda a: a[-1], "{0}[-1]")
op("index", [LIST, INT], INT, lambda a, i: a[i], "{0}[{1}]"); op("take", [LIST, INT], LIST, lambda a, n: a[:n], "{0}[:{1}]"); op("drop", [LIST, INT], LIST, lambda a, n: a[n:], "{0}[{1}:]")
op("count_eq", [LIST, INT], INT, lambda a, n: a.count(n), "{0}.count({1})")
for n, f, p in [("dbl", lambda v: v * 2, "v * 2"), ("inc", lambda v: v + 1, "v + 1"), ("sq", lambda v: v * v, "v * v"), ("negv", lambda v: -v, "-v"), ("absv", abs, "abs(v)")]:
    op("map_" + n, [LIST], LIST, (lambda f: lambda a: [f(v) for v in a])(f), "[" + p + " for v in {0}]")
for n, f, p in [("even", lambda v: v % 2 == 0, "v % 2 == 0"), ("odd", lambda v: v % 2 == 1, "v % 2 == 1"), ("pos", lambda v: v > 0, "v > 0"), ("neg", lambda v: v < 0, "v < 0")]:
    op("keep_" + n, [LIST], LIST, (lambda f: lambda a: [v for v in a if f(v)])(f), "[v for v in {0} if " + p + "]")
op("upper", [STR], STR, str.upper, "{0}.upper()"); op("lower", [STR], STR, str.lower, "{0}.lower()"); op("rev_s", [STR], STR, lambda a: a[::-1], "{0}[::-1]")
op("strip", [STR], STR, str.strip, "{0}.strip()"); op("len_s", [STR], INT, len, "len({0})"); op("split", [STR], SLIST, str.split, "{0}.split()")
op("join", [SLIST], STR, lambda a: " ".join(a), "' '.join({0})"); op("map_len", [SLIST], LIST, lambda a: [len(s) for s in a], "[len(v) for v in {0}]")
op("vowels", [STR], INT, lambda a: sum(c in "aeiou" for c in a), "sum(c in 'aeiou' for c in {0})")

import math
op("keep_gt", [LIST, INT], LIST, lambda a, n: [v for v in a if v > n], "[v for v in {0} if v > {1}]"); op("keep_lt", [LIST, INT], LIST, lambda a, n: [v for v in a if v < n], "[v for v in {0} if v < {1}]")
op("map_add", [LIST, INT], LIST, lambda a, n: [v + n for v in a], "[v + {1} for v in {0}]"); op("map_mul", [LIST, INT], LIST, lambda a, n: [v * n for v in a], "[v * {1} for v in {0}]")
op("contains", [LIST, INT], BOOL, lambda a, n: n in a, "({1} in {0})"); op("concat", [LIST, LIST], LIST, lambda a, b: a + b, "({0} + {1})")
op("zip_add", [LIST, LIST], LIST, lambda a, b: [p + q for p, q in zip(a, b)] if len(a) == len(b) else None, "[p + q for p, q in zip({0}, {1})]")
op("zip_mul", [LIST, LIST], LIST, lambda a, b: [p * q for p, q in zip(a, b)] if len(a) == len(b) else None, "[p * q for p, q in zip({0}, {1})]")
def _cum(a):
    t, o = 0, []
    for v in a: t += v; o.append(t)
    return o
op("cumsum", [LIST], LIST, _cum, "list(__import__('itertools').accumulate({0}))")
op("diffs", [LIST], LIST, lambda a: [q - p for p, q in zip(a, a[1:])], "[q - p for p, q in zip({0}, {0}[1:])]")
op("range_n", [INT], LIST, lambda n: list(range(n)) if 0 <= n <= 200 else None, "list(range({0}))")
op("gcd", [INT, INT], INT, math.gcd, "__gcd({0}, {1})"); op("power", [INT, INT], INT, lambda a, b: a ** b if 0 <= b <= 8 else None, "({0} ** {1})")
op("fact", [INT], INT, lambda n: math.factorial(n) if 0 <= n <= 12 else None, "__fact({0})")
def _prime(n):
    if n < 2: return False
    i = 2
    while i * i <= n:
        if n % i == 0: return False
        i += 1
    return True
op("is_prime", [INT], BOOL, _prime, "__prime({0})"); op("keep_prime", [LIST], LIST, lambda a: [v for v in a if _prime(v)], "[v for v in {0} if __prime(v)]")
op("digits", [INT], LIST, lambda n: [int(c) for c in str(abs(n))], "[int(c) for c in str(abs({0}))]"); op("to_str", [INT], STR, str, "str({0})")
op("to_int", [STR], INT, lambda s: int(s) if s.strip("-").isdigit() else None, "int({0})")
op("is_sorted", [LIST], BOOL, lambda a: a == sorted(a), "({0} == sorted({0}))"); op("any_even", [LIST], BOOL, lambda a: any(v % 2 == 0 for v in a), "any(v % 2 == 0 for v in {0})")
op("all_pos", [LIST], BOOL, lambda a: all(v > 0 for v in a), "all(v > 0 for v in {0})")
op("s_concat", [STR, STR], STR, lambda a, b: a + b, "({0} + {1})"); op("contains_s", [STR, STR], BOOL, lambda a, b: b in a, "({1} in {0})")
op("s_count", [STR, STR], INT, lambda a, b: a.count(b) if b else None, "{0}.count({1})"); op("repeat", [STR, INT], STR, lambda a, n: a * n if 0 <= n <= 20 else None, "({0} * {1})")
op("title", [STR], STR, str.title, "{0}.title()"); op("count_digits", [STR], INT, lambda s: sum(c.isdigit() for c in s), "sum(c.isdigit() for c in {0})")
op("count_upper", [STR], INT, lambda s: sum(c.isupper() for c in s), "sum(c.isupper() for c in {0})")
op("cap_words", [SLIST], SLIST, lambda a: [w.capitalize() for w in a], "[w.capitalize() for w in {0}]"); op("map_upper_s", [SLIST], SLIST, lambda a: [w.upper() for w in a], "[w.upper() for w in {0}]")
op("first_s", [SLIST], STR, lambda a: a[0], "{0}[0]"); op("last_s", [SLIST], STR, lambda a: a[-1], "{0}[-1]")

CONSTS = {INT: [0, 1, 2, 3, 10]}

def type_of(v):
    if isinstance(v, bool): return BOOL
    if isinstance(v, int): return INT
    if isinstance(v, str): return STR
    if isinstance(v, list) and all(isinstance(i, int) and not isinstance(i, bool) for i in v): return LIST
    if isinstance(v, list) and all(isinstance(i, str) for i in v): return SLIST
    raise TypeError("unsupported value")

HELPERS = ("import math, itertools\n"
           "def __gcd(a, b): return math.gcd(a, b)\n"
           "def __fact(n): return math.factorial(n)\n"
           "def __prime(n):\n    if n < 2: return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0: return False\n        i += 1\n    return True\n")

def norm(s):
    s.setdefault("in_types", [s["in_type"]] if "in_type" in s else []); s["in_type"] = s["in_types"][0]; return s

class Library:
    """Skills + custom ops as building blocks. Calling one counts as ONE node: that is how learning shortens the search.
    skill = {id, in_types:[..], out_type, expr}; custom op = {name, args:[types], ret, params:[names], src:'python expression'} (run by safe_eval)."""
    def __init__(self, skills=(), ops=()):
        self.skills = {s["id"]: norm(s) for s in skills}; self.ops = {o["name"]: o for o in ops}
    def table(self):
        t = dict(OPS); args_tpl = lambda n: "(" + ", ".join("{%d}" % i for i in range(n)) + ")"
        for o in self.ops.values():
            t["op:" + o["name"]] = (tuple(o["args"]), o["ret"], _safe(self._ofn(o)), "u_" + o["name"] + args_tpl(len(o["args"])))
        for s in self.skills.values():
            t["skill:" + s["id"]] = (tuple(s["in_types"]), s["out_type"], self._fn(s), s["id"] + args_tpl(len(s["in_types"])))
        return t
    def _fn(self, s): return lambda *a, _s=s: evaluate(_s["expr"], a, self)
    def _ofn(self, o):
        from .safe_eval import run
        return lambda *a, _o=o: run(_o["src"], _o["params"], a)

def evaluate(expr, args, lib=None, table=None):
    """args = tuple of the function's inputs (x, y)."""
    table = table or (lib or Library()).table(); args = tuple(args)
    def go(e):
        k = e[0]
        if k == "x": return args[0]
        if k == "y": return args[1]
        if k == "c": return e[1]
        vals = [go(c) for c in e[1:]]
        if any(a is None for a in vals): return None
        return table[k][2](*vals)
    return go(expr)

def as_args(inp, arity): return tuple(inp) if arity > 1 else (inp,)
def call_skill(skill, lib, inp): return evaluate(skill["expr"], as_args(inp, len(skill["in_types"])), lib)

def render(expr, lib):
    table = lib.table()
    def go(e):
        if e[0] in ("x", "y"): return e[0]
        if e[0] == "c": return repr(e[1])
        return table[e[0]][3].format(*[go(c) for c in e[1:]])
    return go(expr)

def _walk_names(e, out):
    if e[0] not in ("x", "y", "c"):
        out.append(e[0])
        for c in e[1:]: _walk_names(c, out)
    return out
def deps(expr): return [n[6:] for n in _walk_names(expr, []) if n.startswith("skill:")]

def render_function(skill, lib):
    """Full standalone source of a skill with everything it needs (helpers, custom ops, earlier skills) defined first."""
    skills = {**lib.skills, skill["id"]: norm(skill)}; order, seen, ops = [], set(), []
    def visit(sid):
        if sid in seen: return
        seen.add(sid)
        for d in deps(skills[sid]["expr"]): visit(d)
        ops.extend(n[3:] for n in _walk_names(skills[sid]["expr"], []) if n.startswith("op:")); order.append(sid)
    visit(skill["id"]); uniq = []
    for n in ops:
        if n not in uniq: uniq.append(n)
    parts = [HELPERS] if any(n for n in _walk_names(skill["expr"], []) if n in ("gcd", "fact", "is_prime", "keep_prime", "cumsum")) or order[:-1] else []
    parts = [HELPERS]
    for n in uniq:
        o = lib.ops[n]; parts.append(f"def u_{n}({', '.join(o['params'])}):\n    return {o['src'].strip()}\n")
    for sid in order:
        sk = skills[sid]; params = ", ".join("xy"[:len(sk["in_types"])])
        parts.append(f"def {sid}({params}):\n    return {render(sk['expr'], lib)}\n")
    return "\n".join(parts)

def size(e): return 1 if e[0] in ("x", "y", "c") else 1 + sum(size(c) for c in e[1:])

def solve(examples, holdout, lib=None, max_size=7, max_nodes=60000, max_seconds=20.0, arity=1):
    """Smallest program that matches ALL examples and then ALSO the hidden holdout cases. Returns (expr, stats) or (None, stats).
    arity=2: every example input is [a, b] and the program may use both x and y."""
    lib = lib or Library(); table = lib.table(); n_ex = len(examples)
    rows = [as_args(e[0], arity) for e in examples] + [as_args(h[0], arity) for h in holdout]    # holdout INPUTS only help tell programs apart; their outputs are checked at the end
    goal = tuple(_tup(e[1]) for e in examples); hgoal = tuple(_tup(h[1]) for h in holdout); out_t = type_of(examples[0][1])
    bank = {}; seen = set(); nodes = 0; t0 = time.time()
    def add(sz, t, expr, vals):
        nonlocal nodes
        if any(v is None for v in vals): return None
        key = (t, tuple(_tup(v) for v in vals))
        if key in seen: return None
        seen.add(key); nodes += 1; bank.setdefault(sz, {}).setdefault(t, []).append((expr, vals)); return key
    def check(vals, t):
        got = tuple(_tup(v) for v in vals); return t == out_t and got[:n_ex] == goal and got[n_ex:] == hgoal
    for i, name in enumerate("xy"[:arity]): add(1, type_of(rows[0][i]), (name,), [r[i] for r in rows])
    for t, cs in CONSTS.items():
        for c in cs: add(1, t, ("c", c), [c] * len(rows))
    for sz in range(1, max_size + 1):
        if sz > 1:
            for name in sorted(table):
                atypes, rt, fn, _ = table[name]; k = len(atypes)
                for combo in _splits(sz - 1, k):
                    pools = [bank.get(s, {}).get(a, []) for s, a in zip(combo, atypes)]
                    if not all(pools): continue
                    for items in _product(pools):
                        if nodes > max_nodes or time.time() - t0 > max_seconds: return None, {"nodes": nodes, "seconds": round(time.time() - t0, 2), "reason": "budget"}
                        vals = [fn(*[it[1][i] for it in items]) for i in range(len(rows))]
                        expr = (name,) + tuple(it[0] for it in items)
                        if add(sz, rt, expr, vals) and check(vals, rt): return expr, {"nodes": nodes, "size": sz, "seconds": round(time.time() - t0, 2)}
        else:
            for t, items in bank[1].items():
                for expr, vals in items:
                    if check(vals, t): return expr, {"nodes": nodes, "size": 1, "seconds": 0.0}
    return None, {"nodes": nodes, "seconds": round(time.time() - t0, 2), "reason": "not found"}

def _splits(total, k):
    if k == 1: yield (total,); return
    for a in range(1, total - k + 2):
        for rest in _splits(total - a, k - 1): yield (a,) + rest
def _product(pools):
    if len(pools) == 1:
        for p in pools[0]: yield (p,)
        return
    for p in pools[0]:
        for rest in _product(pools[1:]): yield (p,) + rest
