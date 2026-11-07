# -*- coding: utf-8 -*-
"""Learning building blocks from code YOU give it. It reads small pure functions (one `return` expression) out of Python files,
works out their input/output types by trying them, and proposes them as new operations. It NEVER runs the uploaded file:
it only parses it and interprets whitelisted expressions (safe_eval). The develop cycle verifies each proposal before it is installed."""
import ast, re
from .safe_eval import problems, run
from .synth import INT, LIST, STR, SLIST, type_of, OPS, _ok, _tup
from .verify import fuzz_args, verify_op

def extract(source):
    try: tree = ast.parse(source)
    except SyntaxError: return []
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.FunctionDef) or n.decorator_list or n.args.defaults or n.args.vararg or n.args.kwarg or n.args.kwonlyargs: continue
        params = [a.arg for a in n.args.args]
        body = [b for b in n.body if not (isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant))]
        if not (1 <= len(params) <= 2 and len(body) == 1 and isinstance(body[0], ast.Return) and body[0].value is not None): continue
        src = ast.unparse(body[0].value)
        if not problems(src, params): out.append({"fname": n.name, "params": params, "src": src})
    return out

def signatures(c):
    import itertools
    kinds = [INT, LIST, STR, SLIST]; sigs = []
    for combo in itertools.product(kinds, repeat=len(c["params"])):
        rows = fuzz_args(list(combo), 5, 20); res = []
        for r in rows:
            try: v = run(c["src"], c["params"], r)
            except Exception: v = None
            res.append(v if _ok(v) else None)
        good = [v for v in res if v is not None]
        if len(good) < 15: continue
        try: rets = {type_of(v) for v in good}
        except TypeError: continue
        if len(rets) == 1: sigs.append((list(combo), rets.pop(), res))
    return sigs

def propose(source, lib, origin="upload", max_new=20):
    """-> (verified new ops, notes). Duplicates (same behaviour as something already known) are skipped."""
    table = lib.table(); known = {}
    for name, (atypes, rt, fn, _) in table.items():
        rows = fuzz_args(list(atypes), 5, 20)
        known.setdefault((tuple(atypes), rt), []).append(tuple(_tup(fn(*r)) for r in rows))
    new, notes = [], []
    for c in extract(source):
        sigs = signatures(c)
        if not sigs: notes.append(f"{c['fname']}: can't tell its types by trying it"); continue
        for args, ret, res in sigs[:2]:
            vec = tuple(_tup(v) for v in res)
            if vec in known.get((tuple(args), ret), []): notes.append(f"{c['fname']}: already known"); continue
            name = re.sub(r"\W", "_", c["fname"].lower())[:30] + ("_" + "".join(a[0] for a in args) if len(sigs) > 1 else "")
            if name in lib.ops or any(o["name"] == name for o in new): continue
            op = {"name": name, "args": args, "ret": ret, "params": c["params"], "src": c["src"], "origin": origin}
            ok, why = verify_op(op)
            if ok and len(new) < max_new: new.append(op); known.setdefault((tuple(args), ret), []).append(vec); notes.append(f"{c['fname']}: NEW op {name}")
            else: notes.append(f"{c['fname']}: rejected ({'; '.join(why)[:80]})")
    return new, notes
