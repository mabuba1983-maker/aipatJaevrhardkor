# -*- coding: utf-8 -*-
"""A small, FAST, multi-skill benchmark used by the self-development gate (nuwaa/lm/autodev.py). Each skill is scored 0..1 on a handful of fresh
examples (memory off, so nothing is looked up). Kept deliberately small (speed matters: this runs after every training step the gate considers),
but covers the distinct things nuwaa.lm.pretrain_gru's old single "held-out bits/char" number could not see: whether the model still writes code
that runs, still reviews code correctly, still understands basic Arabic/English, not just whether its average character-prediction improved."""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from nuwaa.lm.gru import Session

BLK = re.compile(r"```python\n(.*?)```", re.S)
FBLK = re.compile(r"<<ملف:([^>\n]{1,80})>>\n?(.*?)\n?<<نهاية>>", re.S)

def _run(code, timeout=5):
    import subprocess, sys as _s, tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py"); open(p, "w", encoding="utf-8").write(code)
        try: r = subprocess.run([_s.executable, p], capture_output=True, timeout=timeout, cwd=d, text=True)
        except Exception: return 1, ""
        return r.returncode, r.stdout

def score_pairs(lm, seed=1, n=20):
    """1 - normalized held-out loss on the built-in training data (the old single number; kept as one skill among several, not the only one)."""
    from nuwaa.lm.corpus import all_pairs, fmt
    pairs = all_pairs("data"); held = "\n" + "".join(fmt(*p) for i, p in enumerate(pairs) if i % 53 == 7)
    ids = lm.encode(held[:5000], grow=False)
    return max(0.0, 1.0 - lm.bpc(ids) / 2.0)   # 2.0 bits/char ~ a model that has learned almost nothing; 0 bits/char ~ perfect

def score_files(lm, seed=1, n=10):
    import gen_files as g
    g.R.seed(seed); ok = tot = 0
    while tot < n:
        r = g.gen_one()
        if not r: continue
        q, ref = r; tot += 1
        mr = FBLK.search(ref)
        out = Session(lm, seed=tot + seed).reply(q, learn=False, max_chars=500, temp=0.5, mem_gain=0.0, short_gain=0.0, copy_gain=0.9)[0]
        mo = FBLK.search(out)
        asked = mr.group(1) in q
        if mo and (not asked or mo.group(1) == mr.group(1)):
            ext = mr.group(1).rsplit(".", 1)[-1]
            good = (_run(mo.group(2))[0] == 0 and _run(mo.group(2))[1] == _run(mr.group(2))[1]) if ext == "py" else mo.group(2).strip() == mr.group(2).strip()
            ok += good
    return ok / max(1, tot)

def score_review(lm, seed=1, n=10):
    import gen_seed as g
    from seed_data import REVIEWS, STYLE
    items = REVIEWS + STYLE; g.R.seed(seed); ok = 0
    for i in range(n):
        rid, notes, bad_t, good_t = items[i % len(items)]
        nn, ww, name = g.R.randint(3, 9), g.R.randint(10, 99), g.R.choice(g.NAMES)
        bad = g.fill(bad_t, nn, ww, name); good = g.fill(good_t, nn, ww, name)
        rg, og = _run(good)
        q = "راجع هذا الكود:\n```python\n" + bad + "\n```"
        out = Session(lm, seed=i + seed).reply(q, learn=False, max_chars=700, temp=0.5, mem_gain=0.0, short_gain=0.0)[0]
        blocks = BLK.findall(out)
        if blocks: rc, so = _run(blocks[-1]); ok += (rc == 0 and so.strip() == og.strip())
    return ok / max(1, n)

def score_arabic(lm, seed=1, n=16):
    """Loose recall on the Arabic-curriculum answers (shares enough key words with the real explanation)."""
    import seed_arabic_full as af
    items = af.PHON + af.SARF + af.NAHW + af.BALAGHA + af.IMLAA
    STOP = {"من", "في", "على", "الى", "إلى", "عن", "ان", "أن", "ما", "لا", "هو", "هي", "ثم", "قد", "كل", "التي", "الذي", "هذا", "هذه", "او", "أو"}
    def words(t): return {w for w in re.split(r"[^\w]+", t) if len(w) >= 3 and w not in STOP}
    ok = 0
    for i in range(n):
        qs, ref = items[i % len(items)]
        out = Session(lm, seed=i + seed).reply(qs[0], learn=False, max_chars=500, temp=0.5, mem_gain=0.0, short_gain=0.0, copy_gain=0.0)[0]
        ok += len(words(ref) & words(out)) / max(1, len(words(ref))) >= 0.3
    return ok / max(1, n)

SKILLS = {"pairs": score_pairs, "files": score_files, "review": score_review, "arabic": score_arabic}

def run_all(lm, seed=1, sizes=None):
    sizes = sizes or {"files": 10, "review": 10, "arabic": 16}
    out = {"pairs": score_pairs(lm, seed)}
    for name, fn in SKILLS.items():
        if name == "pairs": continue
        out[name] = fn(lm, seed, sizes.get(name, 10))
    return out
