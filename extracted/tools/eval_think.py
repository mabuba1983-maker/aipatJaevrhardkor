# -*- coding: utf-8 -*-
"""Does the model THINK like the interpreter? Fresh programs (new numbers/names), memory off.
 trace: asked to trace a program -> (a) the final result line equals the real output  (b) the whole trace is exactly the real one
 error: given code + the real error message -> the fixed code it writes runs and prints the right output
Usage: python tools/eval_think.py WEIGHTS [N]"""
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_think as gt, gen_seed as g, gen_tasks
from gen_fix import run_out
from nuwaa.lm.gru import GRULM, Session
BLK = re.compile(r"```python\n(.*?)```", re.S)

def main():
    w = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 30; lm = GRULM.load(w)
    gen_tasks.R.seed(4545); g.R.seed(4545); gt.R.seed(4545)
    progs = []
    while len(progs) < n:
        for qs, c in gen_tasks.T():
            a = gt.trace_answer(c)
            if a and c not in [p[0] for p in progs]: progs.append((c, a))
    progs = progs[:n]; res_ok = full_ok = 0
    for i, (c, ref) in enumerate(progs):
        q = gt.TRACE_Q[0] + "\n" + gt.F + "python\n" + c + "\n" + gt.F
        o = Session(lm, seed=i).reply(q, learn=False, max_chars=1000, temp=0.4, mem_gain=0.0, short_gain=0.0, copy_gain=0.0)[0]
        res = lambda t: (t.split("الناتج:")[-1].strip() if "الناتج:" in t else (t.split("الخطأ:")[-1].strip() if "الخطأ:" in t else None))
        res_ok += res(o) is not None and res(o) == res(ref); full_ok += o.strip() == ref.strip()
    ok = tot = 0
    for rid, notes, bad_t, good_t in (gt.REVIEWS + gt.REVIEWS2) * 2:
        if tot >= n: break
        nn, ww, name = g.R.randint(3, 9), g.R.randint(10, 99), g.R.choice(g.NAMES); bad, good = g.fill(bad_t, nn, ww, name), g.fill(good_t, nn, ww, name)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.py"); open(p, "w", encoding="utf-8").write(bad)
            try: r = subprocess.run([sys.executable, p], capture_output=True, timeout=5, cwd=d, text=True)
            except subprocess.TimeoutExpired: continue
        if r.returncode == 0: continue
        line = (r.stderr.strip().splitlines() or [""])[-1][:160]; rg, og = run_out(good); tot += 1
        q = "هذا الكود يعطي خطأ. حلل الخطأ وأصلحه:\n" + gt.F + "python\n" + bad + "\n" + gt.F + "\nالخطأ الظاهر: " + line
        o = Session(lm, seed=tot).reply(q, learn=False, max_chars=800, temp=0.4, mem_gain=0.0, short_gain=0.0, copy_gain=0.0)[0]
        b = BLK.findall(o)
        if b: rc, so = run_out(b[-1]); ok += (rc == 0 and so.strip() == og.strip())
    print(f"{w}: TRACE final result right {res_ok}/{len(progs)}, whole trace exactly right {full_ok}/{len(progs)} | ERROR fix right {ok}/{tot}")

main()
