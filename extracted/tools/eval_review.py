# -*- coding: utf-8 -*-
"""Code review on FRESH variants (new numbers and names). The model gets the bad code and writes a review; the LAST python block it writes is run and
compared with the correct version's output. Memory OFF. Usage: python tools/eval_review.py WEIGHTS [N]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed as g
from seed_data import REVIEWS, STYLE
from gen_fix import run_out
from nuwaa.lm.gru import GRULM, Session
BLK = re.compile(r"```python\n(.*?)```", re.S)

def main():
    w = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    g.R.seed(4040); lm = GRULM.load(w); items = REVIEWS + STYLE; tot = ok = fmt_ok = 0; notes_ok = 0
    for i in range(n):
        rid, notes, bad_t, good_t = items[i % len(items)]
        nn = g.R.randint(3, 9); ww = g.R.randint(10, 99); name = g.R.choice(g.NAMES)
        bad = g.fill(bad_t, nn, ww, name); good = g.fill(good_t, nn, ww, name)
        rg, og = run_out(good)
        q = g.F + "python\n" + bad + "\n" + g.F
        out = Session(lm, seed=i).reply("راجع هذا الكود:\n" + q, learn=False, max_chars=700, temp=0.5, mem_gain=0.0, short_gain=0.0)[0]
        tot += 1; blocks = BLK.findall(out)
        if not blocks: continue
        fmt_ok += 1; rc, so = run_out(blocks[-1])
        ok += (rc == 0 and so.strip() == og.strip())
        notes_ok += any(k in out for k in notes[0].split()[:2])
    print(f"{w}: reviews {tot} | wrote a code block {fmt_ok} | fixed code right (runs, correct output) {ok}")
main()
