# -*- coding: utf-8 -*-
"""Fresh project requests (new names, numbers, words). Memory OFF, copy-from-request ON. The model writes <<ملف:folder/name>> blocks; they are written to a
temporary folder exactly as the app would, and main.py is RUN. Scores:  blocks (>=2 well-formed files) | folder name as asked | main.py runs | prints exactly
what the reference project prints.  Usage: python tools/eval_projects.py WEIGHTS [N]"""
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed2 as g
from nuwaa.lm.gru import GRULM, Session
BLK = re.compile(r"<<ملف:([^>\n]{1,80})>>\n?(.*?)\n?<<نهاية>>", re.S)

def run_proj(files, entry):
    with tempfile.TemporaryDirectory() as d:
        for rel, c in files.items():
            path = os.path.join(d, rel)
            if ".." in rel or rel.startswith("/"): return None
            os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w", encoding="utf-8").write(c)
        try: r = subprocess.run([sys.executable, os.path.join(d, entry)], cwd=d, capture_output=True, timeout=5, text=True)
        except Exception: return None
        return r.stdout if r.returncode == 0 else None

def main():
    w = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    g.R.seed(909); lm = GRULM.load(w); tot = multi = named = runs = right = 0
    while tot < n:
        desc, p, files, entry, plan = g.make_project()
        if not entry: continue
        q = g.R.choice(g.ASKP).format(d=desc, p=p); tot += 1
        ref = run_proj({f"{p}/{nm}": c for nm, c in files}, f"{p}/{entry}")
        out = Session(lm, seed=tot).reply(q, learn=False, max_chars=1500, temp=0.5, mem_gain=0.0, short_gain=0.0, copy_gain=0.9)[0]
        got = {m.group(1).strip(): m.group(2) + "\n" for m in BLK.finditer(out)}
        if len(got) < 2: continue
        multi += 1; named += all(k.startswith(p + "/") for k in got)
        main_key = next((k for k in got if k.endswith("main.py")), None)
        if not main_key: continue
        o = run_proj(got, main_key)
        if o is not None: runs += 1; right += (o.strip() == (ref or "").strip())
    print(f"{w}: requests {tot} | 2+ files {multi} | folder as asked {named} | main.py runs {runs} | output exactly right {right}")
main()
