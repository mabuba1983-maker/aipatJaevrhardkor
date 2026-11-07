# -*- coding: utf-8 -*-
"""Fresh requests the model never saw (new names, numbers, words). Memory OFF. Scores what the model builds:
 block   : it wrote a well-formed <<ملف:...>> block
 name    : the file name it chose is the one asked for (when one was asked)
 exact   : the file content is exactly right (text/json/csv/md/html) or, for python, the program prints exactly the right output
Usage: python tools/eval_files.py WEIGHTS [N]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_files as g
from gen_fix import run_out
from nuwaa.lm.gru import GRULM, Session
BLK = re.compile(r"<<ملف:([^>\n]{1,80})>>\n?(.*?)\n?<<نهاية>>", re.S)

def main():
    w = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    g.R.seed(777); lm = GRULM.load(w); tot = blk = nm = ex = 0; kinds = {}
    while tot < n:
        r = g.gen_one()
        if not r: continue
        q, ref = r; tot += 1
        out = Session(lm, seed=tot).reply(q, learn=False, max_chars=700, temp=0.5, mem_gain=0.0, short_gain=0.0, copy_gain=float(os.environ.get("COPY", "0.8")))[0]
        mr = BLK.search(ref); mo = BLK.search(out)
        ext = mr.group(1).rsplit(".", 1)[-1]; k = kinds.setdefault(ext, [0, 0]); k[0] += 1
        if not mo: continue
        blk += 1
        asked = mr.group(1) in q
        if (not asked) or mo.group(1) == mr.group(1): nm += 1
        if ext == "py": good = run_out(mo.group(2))[0] == 0 and run_out(mo.group(2))[1] == run_out(mr.group(2))[1]
        else: good = mo.group(2).strip() == mr.group(2).strip()
        ex += good; k[1] += good
    print(f"{w}: requests {tot} | block {blk} | name ok {nm} | content exactly right {ex}")
    print("by type (right/asked):", {e: f"{a[1]}/{a[0]}" for e, a in kinds.items()})
main()
