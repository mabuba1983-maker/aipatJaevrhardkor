# -*- coding: utf-8 -*-
"""Expands tools/seed_data.py into data/v18_seed.jsonl. Every python snippet is RUN: lessons must run (real output appended); in a code review the
good version must run and be right, the bad version must really fail or give a different result (style cases: same result). Output: data/v18_seed.jsonl."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from seed_data import LESSONS, REVIEWS, STYLE, ARABIC
from gen_fix import run_out
from nuwaa.core.benchmark import load_items
EVAL = {i["user"] for i in load_items("data/eval")}
R = random.Random(18); F = "```"
WRAP = ["{q}", "{q}", "{q} لو سمحت", "ممكن {q}", "يا نواة {q}"]
ASK = ["راجع هذا الكود:", "ايش الخطأ في هذا الكود؟", "حسّن هذا الكود:", "عندي كود فيه مشكلة، راجعه:", "ما رأيك في هذا الكود؟"]
NAMES = ["ali", "sara", "omar", "noor", "fahd", "abc", "xyz"]

def fill(t, n, w, name): return t.replace("{n}", str(n)).replace("{w}", str(w)).replace("{name}", name)
def variants(qs):
    out = list(qs)
    for q in qs:
        for wr in R.sample(WRAP, 2):
            v = wr.format(q=q)
            if v not in out: out.append(v)
    return out

def main():
    pairs = []; dropped = []
    for qs, expl, code in LESSONS:
        rc, so = run_out(code)
        if rc != 0: dropped.append(qs[0]); continue
        a = expl + "\nمثال:\n" + F + "python\n" + code + "\n" + F + ("\nالناتج: " + so.strip().replace("\n", " ، ") if so.strip() else "")
        if len(a) <= 1150:
            for q in variants(qs): pairs.append((q, a))
    for style, items in ((False, REVIEWS), (True, STYLE)):
        for rid, notes, bad_t, good_t in items:
            made = 0; tries = 0; seen = set()
            while made < 6 and tries < 40:
                tries += 1
                n = R.randint(3, 9); w = R.randint(10, 99); name = R.choice(NAMES)
                bad = fill(bad_t, n, w, name); good = fill(good_t, n, w, name)
                if (n, w, name) in seen: continue
                seen.add((n, w, name))
                rb, ob = run_out(bad); rg, og = run_out(good)
                if rg != 0: dropped.append(rid + ":good"); break
                if style and (rb != 0 or ob != og): dropped.append(rid + ":style"); break
                same = rb == 0 and ob == og            # a cleanliness issue: both versions give the same result
                head = "ملاحظاتي:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(notes, 1)) + "\nالنسخة الأفضل:\n"
                a = head + F + "python\n" + good + "\n" + F + "\n" + ("الناتج نفسه: " if (style or same) else "الناتج الصحيح: ") + og.strip().replace("\n", " ، ")
                u = R.choice(ASK) + "\n" + F + "python\n" + bad + "\n" + F
                if len(a) <= 1150 and len(u) <= 600: pairs.append((u, a)); made += 1
    for qs, a in ARABIC:
        for q in variants(qs): pairs.append((q, a))
    pairs = [(u, b) for u, b in pairs if u not in EVAL]
    with open("data/v18_seed.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "dropped", dropped)

if __name__ == "__main__": main()
