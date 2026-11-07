# -*- coding: utf-8 -*-
"""Builds data/v16_arabic.jsonl and data/v16_code.jsonl. Every python snippet is RUN (5 s limit) and dropped if it fails."""
import json, os, random, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from v16_arabic import CHAT, CAPS, ARABIC
from v16_code import TASKS, CONCEPTS, F

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nuwaa.core.benchmark import load_items
EVAL = {i["user"] for i in load_items("data/eval")}          # the benchmark questions must never be in the training data (tests/test_stages.py)
R = random.Random(16)
WRAP = ["{q}", "{q}", "{q} لو سمحت", "ممكن {q}", "{q}؟", "يا نواة {q}"]

def variants(qs, n=6):
    out = []
    for q in qs:
        out.append(q)
        for w in R.sample(WRAP, 2):
            v = w.format(q=q)
            if v not in out: out.append(v)
    return out[:max(n, len(qs))]

def runs(code):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py"); open(p, "w", encoding="utf-8").write(code)
        try: r = subprocess.run([sys.executable, p], capture_output=True, timeout=5, cwd=d)
        except Exception: return False
        return r.returncode == 0

def write(path, pairs):
    pairs = [(u, b) for u, b in pairs if u not in EVAL]
    with open(path, "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print(path, len(pairs))

def main():
    ar = []
    for qs, a in CAPS + ARABIC:       # the fixed greeting sentences (CHAT) are replaced by composed ones: tools/gen_files.py
        for q in variants(qs): ar.append((q, a))
    write("data/v16_arabic.jsonl", ar)
    code = []; bad = 0
    for qs, c in TASKS:
        if not runs(c): bad += 1; print("DROPPED:", qs[0]); continue
        ans = "هذا الكود:\n" + F + "python\n" + c + "\n" + F
        if len(ans) > 1150: continue
        for q in variants(qs, 7): code.append((q, ans))
    for qs, a in CONCEPTS:
        for q in variants(qs): code.append((q, a))
    write("data/v16_code.jsonl", code); print("dropped", bad)

if __name__ == "__main__": main()
