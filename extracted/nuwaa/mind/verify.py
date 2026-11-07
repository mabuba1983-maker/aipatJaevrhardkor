# -*- coding: utf-8 -*-
"""A skill counts only if it passes THREE independent checks: (1) the interpreter on the examples, (2) the hidden holdout,
(3) the rendered Python source, run in a separate locked-down process, must agree with the interpreter on random inputs."""
import ast, json, os, random, subprocess, sys, tempfile
from .synth import call_skill, as_args, evaluate, render_function, INT, LIST, STR, SLIST, BOOL, HELPERS
from .safe_eval import FUNCS, METHODS
try: import resource
except ImportError: resource = None

ALLOWED_NAMES = set(FUNCS) | {"zip", "dict", "x", "y", "True", "False", "math", "itertools", "accumulate"}
ALLOWED_ATTRS = set(METHODS) | {"gcd", "factorial", "accumulate"}

def source_problems(src, own_names=()):
    try: tree = ast.parse(src.replace("__import__('itertools')", "itertools"))
    except SyntaxError as e: return [f"syntax: {e}"]
    local = set(own_names); bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.arg): local.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): local.add(n.id)
        elif isinstance(n, ast.FunctionDef): local.add(n.name)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            if any(a.name not in ("math", "itertools") for a in n.names): bad.append("import")
        elif isinstance(n, (ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Lambda, ast.Try, ast.With, ast.AsyncFunctionDef, ast.ClassDef)): bad.append(type(n).__name__)
        elif isinstance(n, ast.Name) and n.id not in ALLOWED_NAMES and n.id not in local: bad.append("name " + n.id)
        elif isinstance(n, ast.Attribute) and n.attr not in ALLOWED_ATTRS: bad.append("attr " + n.attr)
    return bad

def _limits():
    if resource:
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10)); resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))

def fuzz_inputs(t, seed, n=25):
    r = random.Random(seed)
    if t == INT: return [r.randint(-50, 50) for _ in range(n)]
    if t == LIST: return [[r.randint(-9, 12) for _ in range(r.randint(1, 8))] for _ in range(n)]
    words = ["alpha", "Beta", "gamma delta", "level", "  pad ", "x", "AbBa", "one two three", "a1b22"]
    if t == STR: return [" ".join(r.choice(words) for _ in range(r.randint(1, 3))) for _ in range(n)]
    if t == SLIST: return [[r.choice(words) for _ in range(r.randint(1, 5))] for _ in range(n)]
    if t == BOOL: return [r.random() < .5 for _ in range(n)]
    return []

def fuzz_args(types, seed, n=25):
    cols = [fuzz_inputs(t, seed * 7 + i, n) for i, t in enumerate(types)]; return [list(r) for r in zip(*cols)]

def run_source(src, name, arg_rows, timeout=15):
    script = src + "\nimport json,sys\n_in=json.loads(sys.stdin.read())\n_o=[]\nfor _a in _in:\n    try: _o.append(" + name + "(*_a))\n    except Exception: _o.append(None)\nprint(json.dumps(_o))\n"
    d = tempfile.mkdtemp(prefix="nuwaa_skill_")
    try:
        r = subprocess.run([sys.executable, "-I", "-c", script], cwd=d, env={"PATH": os.environ.get("PATH", "")}, input=json.dumps(arg_rows), capture_output=True,
                           text=True, timeout=timeout, preexec_fn=_limits if resource else None)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except Exception: return None

def verify_skill(skill, lib, task_cases=(), seeds=(1, 2, 3)):
    """Returns (ok, [reasons]). `task_cases` are [[input, output], ...] (examples + holdout)."""
    from .synth import norm
    skill = norm(skill); why = []; table = lib.table(); k = len(skill["in_types"])
    for i, o in task_cases:
        if evaluate(skill["expr"], as_args(i, k), lib, table) != o: why.append(f"interpreter disagrees with a case: {i!r}")
    src = render_function(skill, lib); pb = source_problems(src, set(lib.skills) | {skill["id"]})
    if pb: return False, why + ["unsafe/unknown source: " + ", ".join(sorted(set(pb)))]
    for seed in seeds:                                                      # slow on purpose: several independent random batches
        rows = fuzz_args(skill["in_types"], seed); exp = [evaluate(skill["expr"], r, lib, table) for r in rows]
        got = run_source(src, skill["id"], rows)
        if got is None: why.append("sandbox run failed"); break
        for r, e, g in zip(rows, exp, got):
            if e is not None and e != g: why.append(f"source disagrees with interpreter on {r!r}: {e!r} vs {g!r}"); break
    if task_cases:
        got = run_source(src, skill["id"], [list(as_args(c[0], k)) for c in task_cases])
        if got is None or any(g != c[1] for g, c in zip(got, task_cases)): why.append("source fails the task cases")
    return (not why), why

def verify_op(op, seeds=(1, 2, 3)):
    """A new building block taken from outside code: (1) only whitelisted syntax, (2) deterministic, (3) the rendered source, run in a locked-down
    process, agrees with the interpreter on random inputs."""
    from .safe_eval import problems, run
    pb = problems(op["src"], op["params"])
    if pb: return False, ["not allowed: " + ", ".join(pb)]
    src = f"def u_{op['name']}({', '.join(op['params'])}):\n    return {op['src'].strip()}\n"; bad = source_problems(src)
    if bad: return False, ["unsafe source: " + ", ".join(sorted(set(bad)))]
    why = []
    for seed in seeds:
        rows = fuzz_args(op["args"], seed)
        def one(r):
            try: return run(op["src"], op["params"], r)
            except Exception: return None
        exp = [one(r) for r in rows]
        if exp != [one(r) for r in rows]: why.append("not deterministic"); break
        got = run_source(HELPERS + src, "u_" + op["name"], rows)
        if got is None: why.append("sandbox run failed"); break
        for r, e, g in zip(rows, exp, got):
            if e is not None and e != g: why.append(f"source disagrees on {r!r}"); break
    return (not why), why
