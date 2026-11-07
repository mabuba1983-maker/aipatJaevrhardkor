# -*- coding: utf-8 -*-
"""Teaches the model to THINK about Python code the way the interpreter does. Everything is produced by really running the code:
  1. a CATALOG of built-ins and methods (Arabic explanation + example + the real output)
  2. EXECUTION TRACES: line by line, which variables changed and to what (sys.settrace), then the real output or the real error
  3. ERROR ANALYSIS: code + the real error message the interpreter printed -> why it happened -> the fixed code and its real output
No sentence of the traces is written by hand: the numbers and values come from the run. Output: data/v20_think.jsonl"""
import contextlib, io, json, os, random, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed as g, gen_tasks
from gen_fix import run_out
from seed_data import LESSONS, REVIEWS, STYLE
from seed_data2 import ALGO, REVIEWS2
from seed_data3 import CATALOG
from v16_code import TASKS
R = random.Random(20); F = "```"

class _Stop(Exception): pass

def trace_run(code, maxlines=22):
    """(events, output, error) of really running `code`; events = [(line, {var: repr}, function)]. None if it needs more than maxlines steps."""
    events = []; st = {"last": None, "snaps": {}}; out = io.StringIO(); err = [None]
    def snap(fr): return {k: repr(v)[:40] for k, v in fr.f_locals.items() if not k.startswith("__") and not callable(v) and not isinstance(v, type(sys))}
    def flush():
        if st["last"]:
            fr, ln, fn = st["last"]; cur = snap(fr); prev = st["snaps"].get(id(fr), {})
            events.append((ln, {k: v for k, v in cur.items() if prev.get(k) != v}, fn)); st["snaps"][id(fr)] = cur; st["last"] = None
    def tracer(frame, event, arg):
        if frame.f_code.co_filename != "<trace>": return None
        if event == "line":
            flush(); st["last"] = (frame, frame.f_lineno, frame.f_code.co_name)
            if len(events) >= maxlines: raise _Stop()
        elif event in ("return", "exception"): flush()
        return tracer
    try: co = compile(code, "<trace>", "exec")
    except SyntaxError: return None
    old = os.getcwd(); d = tempfile.mkdtemp(); os.chdir(d)
    try:
        sys.settrace(tracer)
        try:
            with contextlib.redirect_stdout(out): exec(co, {"__name__": "__trace__"})
        except _Stop: return None
        except BaseException as e: err[0] = f"{type(e).__name__}: {e}"
        finally: sys.settrace(None)
    finally: os.chdir(old)
    flush()
    return events, out.getvalue(), err[0]

def trace_answer(code):
    if any(w in code for w in ("import random", "import time", "input(", "perf_counter", "today()", "id(")): return None
    r = trace_run(code)
    if r is None: return None
    events, out, err = r
    if not events or len(events) > 22: return None
    steps = []
    for i, (ln, ch, fn) in enumerate(events, 1):
        where = f"سطر {ln}" + (f" (داخل {fn})" if fn != "<module>" else "")
        steps.append(f"{i}) {where}: " + (" ، ".join(f"{k} = {v}" for k, v in ch.items()) if ch else "تنفيذ"))
    res = ("الخطأ: " + err) if err else ("الناتج: " + (out.strip().replace("\n", " ، ") if out.strip() else "لا شيء مطبوع"))
    a = "تتبع التنفيذ:\n" + "\n".join(steps) + "\n" + res
    return a if len(a) <= 1150 else None

TRACE_Q = ["تتبّع تنفيذ هذا الكود سطرا سطرا:", "فكّر خطوة خطوة: ماذا يحدث عند تشغيل هذا الكود؟", "ما ناتج هذا الكود؟ تتبّعه أولا.", "اشرح لي كيف ينفذ بايثون هذا الكود:"]
CAT_Q = ["اشرح {n} في بايثون مع مثال", "ما فائدة {n} في بايثون؟", "كيف أستخدم {n} في بايثون", "ماذا تفعل {n}؟"]

def pool():
    codes = [c for _, _, c in CATALOG] + [c for _, _, c in LESSONS] + [c for *_, c in ALGO] + [c for _, c in TASKS]
    for _ in range(35):
        for qs, c in gen_tasks.T(): codes.append(c)
    for rid, notes, bad_t, good_t in REVIEWS + STYLE + REVIEWS2:
        for _ in range(3):
            n, w, name = R.randint(3, 9), R.randint(10, 99), R.choice(g.NAMES); codes += [g.fill(good_t, n, w, name), g.fill(bad_t, n, w, name)]
    seen = set(); out = []
    for c in codes:
        if c not in seen: seen.add(c); out.append(c)
    return out

def main():
    pairs = []; dropped = 0
    for name, desc, code in CATALOG:
        rc, so = run_out(code)
        if rc != 0: dropped += 1; print("catalog dropped:", name); continue
        a = desc + "\nمثال:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
        if len(a) <= 1150:
            for q in R.sample(CAT_Q, 3): pairs.append((q.format(n=name), a))
    n_trace = 0
    for code in pool():
        a = trace_answer(code)
        if a is None: continue
        pairs.append((R.choice(TRACE_Q) + "\n" + F + "python\n" + code + "\n" + F, a)); n_trace += 1
    n_err = 0
    for rid, notes, bad_t, good_t in REVIEWS + REVIEWS2:
        made = 0
        for _ in range(12):
            if made >= 5: break
            n, w, name = R.randint(3, 9), R.randint(10, 99), R.choice(g.NAMES); bad, good = g.fill(bad_t, n, w, name), g.fill(good_t, n, w, name)
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "t.py"); open(p, "w", encoding="utf-8").write(bad)
                try: r = subprocess.run([sys.executable, p], capture_output=True, timeout=5, cwd=d, text=True)
                except subprocess.TimeoutExpired: continue
            if r.returncode == 0: break              # this bug type does not raise: it is covered by the review data
            line = (r.stderr.strip().splitlines() or [""])[-1][:160]; rg, og = run_out(good)
            if rg != 0 or not line: continue
            a = "التحليل: " + notes[0] + "\nالإصلاح: " + notes[1] + "\n" + F + "python\n" + good + "\n" + F + "\nالناتج الصحيح: " + og.strip().replace("\n", " ، ")
            u = "هذا الكود يعطي خطأ. حلل الخطأ وأصلحه:\n" + F + "python\n" + bad + "\n" + F + "\nالخطأ الظاهر: " + line
            if len(a) <= 1150 and u not in g.EVAL: pairs.append((u, a)); made += 1; n_err += 1
    with open("data/v20_think.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "| catalog", len(CATALOG) - dropped, "| traces", n_trace, "| error analyses", n_err)

if __name__ == "__main__": main()
