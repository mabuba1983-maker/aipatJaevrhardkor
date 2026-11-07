# -*- coding: utf-8 -*-
"""A tiny INTERPRETER for pure expressions (no exec/eval). It runs code that came from outside (files you send): only whitelisted nodes,
builtins and methods, a step limit and size limits. Anything else is rejected BEFORE it is ever run."""
import ast, operator, warnings

FUNCS = {"len": len, "sum": sum, "max": max, "min": min, "sorted": sorted, "abs": abs, "list": list, "reversed": lambda a: list(reversed(a)), "str": str,
         "int": int, "bool": bool, "any": any, "all": all, "round": round, "set": set, "range": lambda *a: range(*a), "tuple": tuple}
METHODS = {"upper", "lower", "strip", "lstrip", "rstrip", "split", "join", "count", "startswith", "endswith", "isdigit", "isalpha", "isupper", "islower", "title",
           "capitalize", "replace", "find", "index", "fromkeys"}
BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
       ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}
import math
def _prime(n):
    if n < 2: return False
    i = 2
    while i * i <= n:
        if n % i == 0: return False
        i += 1
    return True
FUNCS.update({"__gcd": math.gcd, "__fact": lambda n: math.factorial(n) if 0 <= n <= 12 else (_ for _ in ()).throw(ValueError()), "__prime": _prime})
class Limit(Exception): pass
_cache = {}

def parse(src):
    if src not in _cache:
        with warnings.catch_warnings(): warnings.simplefilter("ignore"); _cache[src] = ast.parse(src.strip(), mode="eval").body
    return _cache[src]

def problems(src, params):
    """Why this expression may NOT be run (empty list = allowed)."""
    try: tree = parse(src)
    except Exception as e: return [f"syntax: {e}"]
    bad = []; scope = set(params)
    for n in ast.walk(tree):
        if isinstance(n, ast.comprehension):
            if not isinstance(n.target, ast.Name) or n.is_async: bad.append("complex comprehension")
            else: scope.add(n.target.id)
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id not in scope and n.id not in FUNCS and n.id not in ("True", "False", "None"): bad.append("name " + n.id)
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name): ok = f.id in FUNCS
            elif isinstance(f, ast.Attribute): ok = f.attr in METHODS
            else: ok = False
            if not ok or n.keywords and any(k.arg is None for k in n.keywords): bad.append("call not allowed")
        elif isinstance(n, ast.Attribute) and n.attr not in METHODS: bad.append("attr " + n.attr)
        elif isinstance(n, ast.BinOp) and type(n.op) not in BIN: bad.append("operator " + type(n.op).__name__)
        elif isinstance(n, ast.Compare) and any(type(o) not in CMP for o in n.ops): bad.append("comparison")
        elif isinstance(n, (ast.Lambda, ast.Await, ast.Yield, ast.NamedExpr, ast.JoinedStr, ast.Dict, ast.DictComp, ast.SetComp)): bad.append(type(n).__name__)
    return sorted(set(bad))

def run(src, params, args, max_steps=20000):
    tree = parse(src); steps = [0]
    def go(n, env):
        steps[0] += 1
        if steps[0] > max_steps: raise Limit()
        t = type(n)
        if t is ast.Constant: return n.value
        if t is ast.Name: return env[n.id] if n.id in env else FUNCS[n.id] if n.id in FUNCS else {"True": True, "False": False, "None": None}[n.id]
        if t is ast.BinOp:
            a, b = go(n.left, env), go(n.right, env)
            if isinstance(n.op, ast.Pow) and (abs(b) > 12 or abs(a) > 10 ** 4): raise Limit()
            if isinstance(n.op, ast.Mult) and isinstance(a, (str, list)) and b > 200 or isinstance(b, (str, list)) and isinstance(a, int) and a > 200: raise Limit()
            return BIN[type(n.op)](a, b)
        if t is ast.UnaryOp: v = go(n.operand, env); return -v if isinstance(n.op, ast.USub) else +v if isinstance(n.op, ast.UAdd) else (not v)
        if t is ast.BoolOp:
            for i, v in enumerate(n.values):
                r = go(v, env)
                if isinstance(n.op, ast.And) and not r or isinstance(n.op, ast.Or) and r: return r
            return r
        if t is ast.Compare:
            left = go(n.left, env)
            for o, c in zip(n.ops, n.comparators):
                right = go(c, env)
                if not CMP[type(o)](left, right): return False
                left = right
            return True
        if t is ast.IfExp: return go(n.body, env) if go(n.test, env) else go(n.orelse, env)
        if t is ast.Subscript:
            v = go(n.value, env); s = n.slice
            if isinstance(s, ast.Slice): return v[go(s.lower, env) if s.lower else None:go(s.upper, env) if s.upper else None:go(s.step, env) if s.step else None]
            return v[go(s, env)]
        if t in (ast.List, ast.Tuple): return [go(e, env) for e in n.elts] if t is ast.List else tuple(go(e, env) for e in n.elts)
        if t is ast.Call:
            f = n.func; a = [go(x, env) for x in n.args]
            if isinstance(f, ast.Name):
                if f.id == "range" and any(abs(v) > 1000 for v in a): raise Limit()
                return FUNCS[f.id](*a)
            return getattr(go(f.value, env), f.attr)(*a)
        if t in (ast.ListComp, ast.GeneratorExp):
            g = n.generators[0]; out = []
            for v in go(g.iter, env):
                e2 = {**env, g.target.id: v}
                if all(go(c, e2) for c in g.ifs): out.append(go(n.elt, e2))
                if len(out) > 5000: raise Limit()
            return out
        raise Limit()
    return go(tree, dict(zip(params, args)))
