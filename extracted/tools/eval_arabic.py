# -*- coding: utf-8 -*-
"""Quick check: given a fresh phrasing of each Arabic-curriculum question, does the model's reply share enough content words with the real answer?
This is a loose recall check (word overlap), not exact match, since these are long explanatory answers. Usage: python tools/eval_arabic.py WEIGHTS [N]"""
import os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from seed_arabic_full import PHON, SARF, NAHW, BALAGHA, IMLAA, ARUD, ADAB
from nuwaa.lm.gru import GRULM, Session
EXTRA_WRAP = ["وضّح لي: {q}", "عايز أفهم {q}", "{q} بشكل مختصر"]
STOP = {"من", "في", "على", "علي", "الى", "إلى", "عن", "ان", "أن", "ما", "لا", "هو", "هي", "ثم", "قد", "كل", "لم", "لن", "التي", "الذي",
        "ذلك", "هذا", "هذه", "او", "أو", "اذا", "إذا", "بل", "كان", "انه", "إنه", "مع", "بين", "بعد", "قبل", "عند", "كما", "مثل"}
def words(t): return {w for w in __import__("re").split(r"[^\w]+", t) if len(w) >= 3 and w not in STOP}

def main():
    w = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    R = random.Random(909); lm = GRULM.load(w); items = PHON + SARF + NAHW + BALAGHA + IMLAA + ARUD + ADAB
    tot = ok = ok50 = 0
    for i in range(n):
        qs, ref = items[i % len(items)]
        q = R.choice(EXTRA_WRAP).format(q=R.choice(qs))
        o = Session(lm, seed=i).reply(q, learn=False, max_chars=600, temp=0.5, mem_gain=0.0, short_gain=0.0, copy_gain=0.0)[0]
        rw = words(ref); ow = words(o); overlap = len(rw & ow) / max(1, len(rw)); tot += 1
        ok += overlap >= 0.3; ok50 += overlap >= 0.5
    print(f"{w}: fresh-wording questions {tot} | reply shares >=30% of the real answer's key words {ok} | >=50% {ok50}")
main()
