# -*- coding: utf-8 -*-
"""Self-play with a verifier (the model trains itself, on what is PROVEN).

One round:  fresh tasks (new numbers every time, reference answer computed by running real code)
         -> the model WRITES its own answer, letter by letter (memory off: no n-gram recall, no lookup)
         -> the code is run in a throwaway sandbox and its real output is compared with the reference, AND with the output the model claimed
         -> only answers that are proven right become training data (the model's own words, not copies)
         -> a short, gentle training on them mixed with rehearsal of the old data
         -> kept only if the pass rate on a separate fixed test did not drop and the rehearsal text did not get worse; otherwise rolled back.

Safety rules of this project are kept: weights change only after a human button press (single use, expires); a --dry round changes nothing.
This file is not in the protected gate list and never edits the gate, the sandbox or the button. The candidate goes to weights/nlm2_selfplay.npz;
nothing replaces nlm2.npz automatically."""
import argparse, ast, json, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path
try: import resource
except ImportError: resource = None
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import numpy as np
from nuwaa.lm.gru import GRULM, Session
from nuwaa.lm.corpus import all_pairs, fmt
from nuwaa.selfimprove.button import consume_press

FORBIDDEN_IMPORTS = {"socket", "requests", "urllib", "http", "ftplib", "smtplib", "ctypes", "subprocess", "shutil", "os", "sys", "pathlib", "importlib"}
FORBIDDEN_CALLS = {"eval", "exec", "__import__", "open", "compile", "input", "globals", "locals", "getattr", "setattr", "delattr"}
BLOCK = re.compile(r"```python\n(.*?)```", re.S)

def extract(text):
    m = BLOCK.search(text)
    return m.group(1) if m else None

def claimed_output(text):
    if "الناتج:" not in text: return None
    return text.split("الناتج:", 1)[1].strip().replace(" ، ", "\n").strip()

def static_ok(code):
    """Refuse code that touches files, the network, the system or dynamic execution BEFORE it is ever run."""
    try: tree = ast.parse(code)
    except SyntaxError: return False
    for n in ast.walk(tree):
        mods = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else [(n.module or "").split(".")[0]] if isinstance(n, ast.ImportFrom) else []
        if any(m in FORBIDDEN_IMPORTS for m in mods): return False
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in FORBIDDEN_CALLS: return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("__"): return False
    return len(code) < 1500

def _limits():
    if resource:
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5)); resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))

def run_output(code, timeout=5):
    """(ok, stdout): isolated interpreter, throwaway directory, minimal environment, CPU/RAM/time limits."""
    d = tempfile.mkdtemp(prefix="nuwaa_sp_")
    Path(d, "t.py").write_text(code, encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, "-I", "t.py"], cwd=d, env={"PATH": os.environ.get("PATH", "")}, capture_output=True, timeout=timeout,
                           preexec_fn=_limits if resource else None, text=True)
        return r.returncode == 0, r.stdout
    except Exception:
        return False, ""

def verify(text, ref_out, strict=False):
    """Proven right = the code is safe, runs, and prints exactly the reference output. With strict=True the output the model CLAIMED must also be
    right (predicting a result in advance is a second, harder skill; it is measured separately and corrected, not required, when learning)."""
    code = extract(text)
    if code is None or not static_ok(code): return False, code
    ok, out = run_output(code)
    if not ok or out.strip() != ref_out.strip(): return False, code
    if strict:
        cl = claimed_output(text)
        return (cl is not None and cl == ref_out.strip()), code
    return True, code

def with_true_output(text, ref_out):
    """The model's own code and words, with the result line replaced by the REAL output (so it never learns a wrong claim)."""
    head = text.split("الناتج:", 1)[0].rstrip()
    return head + "\nالناتج: " + ref_out.strip().replace("\n", " ، ")

def fresh_tasks(seed, n, banned):
    import gen_tasks
    from gen_fix import run_out
    gen_tasks.R.seed(seed); out = []; seen = set()
    while len(out) < n:
        for qs, ref in gen_tasks.T():
            q = gen_tasks.R.choice(qs)
            if q in banned or q in seen: continue
            rc, so = run_out(ref)
            if rc != 0: continue
            seen.add(q); out.append((q, so))
            if len(out) >= n: break
    return out

def generate(lm, q, seed, temp):
    s = Session(lm, seed=seed)
    return s.reply(q, learn=False, max_chars=520, temp=temp, mem_gain=0.0, short_gain=0.0)[0]       # memory OFF: it must write, not look up

def pass_rate(lm, tasks, seed0=0):
    """(share whose code is right, share whose code AND claimed result are right)."""
    ok = strict = 0
    for i, (q, ref) in enumerate(tasks):
        t = generate(lm, q, seed0 + i, 0.6); ok += verify(t, ref)[0]; strict += verify(t, ref, True)[0]
    n = max(1, len(tasks)); return ok / n, strict / n

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/nlm2.npz"); ap.add_argument("--out", default="weights/nlm2_selfplay.npz")
    ap.add_argument("--tasks", type=int, default=40); ap.add_argument("--samples", type=int, default=2); ap.add_argument("--test", type=int, default=30)
    ap.add_argument("--epochs", type=int, default=2); ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    ap.add_argument("--dry", action="store_true", help="generate and verify only; change nothing and need no button press")
    ap.add_argument("--press", default="self_improve_press.json"); a = ap.parse_args(argv)
    if not a.dry: consume_press(a.press)                                   # one human press = one round
    lm = GRULM.load(a.weights)
    train_users = {u for u, _ in all_pairs(str(ROOT / "data"))}; train_bots = {b for _, b in all_pairs(str(ROOT / "data"))}
    test = fresh_tasks(4242, a.test, train_users)                          # fixed test, never trained on
    tasks = fresh_tasks(a.seed, a.tasks, train_users | {q for q, _ in test})
    t0 = time.time(); before, before_strict = pass_rate(lm, test)
    good = []; novel = 0; tried = 0
    for i, (q, ref) in enumerate(tasks):
        for k in range(a.samples):
            tried += 1; text = generate(lm, q, a.seed * 100 + i * 7 + k, (0.6, 0.85)[k % 2]); ok, code = verify(text, ref)
            if ok:
                good.append((q, with_true_output(text, ref))); novel += text not in train_bots; break
    rep = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "tasks": len(tasks), "samples_tried": tried, "proven": len(good), "proven_not_in_training": novel,
           "code_correct_before": round(before, 3), "code_and_claimed_result_correct_before": round(before_strict, 3), "dry": a.dry}
    if not a.dry and good:
        reh = random.Random(a.seed).sample(all_pairs(str(ROOT / "data")), min(300, len(all_pairs(str(ROOT / "data")))))
        rtxt = "".join(fmt(u, b) for u, b in reh); rids = lm.encode(rtxt, grow=False); rb = lm.bpc(rids)
        snap = {k: v.copy() for k, v in lm.P.items()}
        mix = lm.encode("".join(fmt(u, b) for u, b in good) * 2 + rtxt, grow=False)
        lm.train_stream(mix, B=8, T=96, epochs=a.epochs, lr=a.lr, seed=a.seed)
        after, after_strict = pass_rate(lm, test); ra = lm.bpc(rids)
        rep.update(code_correct_after=round(after, 3), code_and_claimed_result_correct_after=round(after_strict, 3), rehearsal_bpc_before=round(rb, 3), rehearsal_bpc_after=round(ra, 3))
        if after >= before and ra <= rb * 1.03:
            lm.save(str(ROOT / a.out)); rep["result"] = "kept: candidate saved to " + a.out + " (nlm2.npz untouched)"
        else:
            rep["result"] = "rolled back: the test pass rate dropped or the old data got worse"
    elif not a.dry: rep["result"] = "nothing proven this round: nothing to learn"
    rep["seconds"] = round(time.time() - t0)
    (ROOT / "learned").mkdir(exist_ok=True)
    with open(ROOT / "learned" / "selfplay_log.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps(rep, ensure_ascii=False) + "\n")
    print(json.dumps(rep, ensure_ascii=False, indent=1)); return rep

if __name__ == "__main__": main()
