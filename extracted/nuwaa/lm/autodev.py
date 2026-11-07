# -*- coding: utf-8 -*-
"""The self-development ENGINE: trains the model and only accepts a step if no tracked skill got worse.

The old gate (nuwaa.lm.pretrain_gru) watched a single number: bits-per-character on a random held-out slice of the training pairs. That number can
improve while the model's actual abilities get worse — which is exactly what happened when training on the advanced-programming data: the pairs
score improved (0.437 vs 0.411 bits/char) while code-review and trace accuracy both fell. A single average cannot see that kind of trade-off.

This engine instead measures several INDEPENDENT skills (nuwaa.lm.skills_bench: pairs, file-building, code-review, Arabic recall) before and after
each training round, and keeps the new weights ONLY if every tracked skill is within `tolerance` of its old score (a skill may even improve while
another stays flat; it may never drop more than the tolerance). Otherwise it rolls back and, optionally, lowers the learning rate and retries.
This makes "self-development" closer to its name: development that cannot quietly make the model worse at something it already could do.

Usage:
  python -m nuwaa.lm.autodev --init weights/nlm2.npz --out weights/nlm2_auto.npz --rounds 6 --minutes-per-round 5
  python -m nuwaa.lm.autodev --init weights/nlm2.npz --out weights/nlm2_auto.npz --rounds 6 --text extra.txt   # extra data from tools/prepare_corpus.py
"""
import argparse, copy, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from nuwaa.lm.gru import GRULM
from nuwaa.lm.corpus import all_pairs, fmt
from nuwaa.lm import skills_bench as sb

DEFAULT_TOLERANCE = 0.08   # a skill may drop at most 8% of its own prior score before the round is rejected

def measure(lm, seed=1, sizes=None):
    return sb.run_all(lm, seed=seed, sizes=sizes)

def accepts(before, after, tolerance=DEFAULT_TOLERANCE):
    """True if no skill in `after` dropped by more than `tolerance` relative to `before`. Returns (ok, detail per skill)."""
    detail = {}; ok = True
    for k, b in before.items():
        a = after.get(k, 0.0); drop = (b - a) / b if b > 1e-9 else (0.0 if a >= b else 1.0)
        detail[k] = {"before": round(b, 4), "after": round(a, 4), "drop": round(drop, 4)}
        if drop > tolerance: ok = False
    return ok, detail

def one_round(lm, texts, minutes, lr, seed):
    """One bounded training round: reuses GRULM.train_stream (the same stateful truncated-BPTT loop nuwaa.lm.pretrain_gru uses), mutating `lm`
    in place. Callers snapshot the weights before calling this and restore them if the round is rejected."""
    ids = lm.encode("".join(texts), grow=False)
    lm.train_stream(ids, B=16, T=96, epochs=10_000, lr=lr, seed=seed, max_seconds=minutes * 60)   # epochs is a cap; max_seconds ends it on time

def run(init, out, rounds=6, minutes_per_round=5, lr=8e-4, tolerance=DEFAULT_TOLERANCE, text=None, seed=1, log=print):
    lm = GRULM.load(init)
    pairs = all_pairs(str(ROOT / "data")); texts = [fmt(u, b) for u, b in pairs]
    if text: texts += [(l.rstrip("\n").replace("\tج:", "\nج:", 1) + "\n") for l in open(text, encoding="utf-8") if l.strip()]
    before = measure(lm, seed=seed); log(f"starting scores: {before}")
    history = []; accepted_rounds = 0
    for r in range(1, rounds + 1):
        snap = {k: v.copy() for k, v in lm.P.items()}
        one_round(lm, texts, minutes_per_round, lr, seed=seed * 1000 + r)
        after = measure(lm, seed=seed + r)
        ok, detail = accepts(before, after, tolerance)
        history.append({"round": r, "accepted": ok, "detail": detail})
        if ok:
            before = after; accepted_rounds += 1; lm.save(out); log(f"round {r}: ACCEPTED — {detail}")
        else:
            for k in lm.P: lm.P[k][...] = snap[k]
            lr *= 0.6; log(f"round {r}: REJECTED (a skill dropped beyond {tolerance * 100:.0f}%), rolled back, lr -> {lr:.2e} — {detail}")
    (Path(out).with_suffix(".autodev.json")).write_text(json.dumps({"tolerance": tolerance, "accepted_rounds": accepted_rounds, "history": history}, indent=1, ensure_ascii=False), encoding="utf-8")
    return accepted_rounds, history

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--init", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int, default=6); ap.add_argument("--minutes-per-round", type=float, default=5)
    ap.add_argument("--lr", type=float, default=8e-4); ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    ap.add_argument("--text", default=""); ap.add_argument("--seed", type=int, default=1); a = ap.parse_args(argv)
    n, hist = run(a.init, a.out, a.rounds, a.minutes_per_round, a.lr, a.tolerance, a.text or None, a.seed)
    print(f"accepted {n}/{a.rounds} rounds")

if __name__ == "__main__": main()
