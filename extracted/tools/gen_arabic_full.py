# -*- coding: utf-8 -*-
"""Expands tools/seed_arabic_full.py into data/v22_arabic_full.jsonl (no code to run here: these are linguistic facts, hand-checked by Claude, not generated)."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gen_v16 import EVAL
from seed_arabic_full import PHON, SARF, NAHW, BALAGHA, IMLAA, ARUD, ADAB
R = random.Random(22)
WRAP = ["{q}", "{q}", "{q}؟", "ممكن {q}", "يا نواة {q}", "اشرح لي: {q}"]

def variants(qs, n=6):
    out = list(qs)
    for q in qs:
        for w in R.sample(WRAP, 2):
            v = w.format(q=q)
            if v not in out: out.append(v)
    return out[:max(n, len(qs))]

def main():
    pairs = []
    for section in (PHON, SARF, NAHW, BALAGHA, IMLAA, ARUD, ADAB):
        for qs, a in section:
            for q in variants(qs):
                if q not in EVAL: pairs.append((q, a))
    with open("data/v22_arabic_full.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    counts = {n: len(s) for n, s in (("phon", PHON), ("sarf", SARF), ("nahw", NAHW), ("balagha", BALAGHA), ("imlaa", IMLAA), ("arud", ARUD), ("adab", ADAB))}
    print("pairs", len(pairs), "| base items per section:", counts, "| total base items:", sum(counts.values()))

if __name__ == "__main__": main()
