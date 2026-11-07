# -*- coding: utf-8 -*-
"""Train / grow the language model.   python -m nuwaa.mind.lmtrain --out weights/mind_lm.npz --pairs 30000 --epochs 12"""
import argparse, time
import numpy as np
from collections import Counter
from pathlib import Path
from .lm import LM, build_dataset, code_tokens, word_tokens
from .lmdata import random_pairs, lesson_pairs

def vocab_from(pairs, min_tok=2, min_word=2, max_words=2500):
    tc = Counter(t for _, c in pairs for t in code_tokens(c)); wc = Counter(w for d, _ in pairs for w in word_tokens(d))
    return [t for t, n in tc.most_common() if n >= min_tok], [w for w, n in wc.most_common(max_words) if n >= min_word]

def split(pairs, val_frac=.05):
    import hashlib
    tr, va = [], []
    for p in pairs: (va if int(hashlib.md5(p[1].encode()).hexdigest(), 16) % 100 < val_frac * 100 else tr).append(p)
    return tr, va

def val_set(lm, va): X, Y, EX, PW = build_dataset(lm, va); return X, Y, EX, PW

def train(lm, pairs, epochs, lr=3e-3, say=print, max_seconds=None, seed=0):
    tr, va = split(pairs); toks, words = vocab_from(tr, 2, 2); lm.add_vocab(toks, words)
    X, Y, EX, PW = build_dataset(lm, tr); v = val_set(lm, va); say(f"train positions {len(Y)}, val positions {len(v[1])}, params {lm.n_params()}")
    before = lm.perplexity(*v); lm.fit(X, Y, EX, PW, epochs=epochs, lr=lr, say=say, val=v, max_seconds=max_seconds, seed=seed)
    return {"val_ppl_before": before, "val_ppl": lm.perplexity(*v), "train_pairs": len(tr), "val_pairs": len(va)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="weights/mind_lm.npz"); ap.add_argument("--pairs", type=int, default=30000); ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--H", type=int, default=384); ap.add_argument("--init", default=None); ap.add_argument("--seed", type=int, default=11); ap.add_argument("--lr", type=float, default=3e-3); ap.add_argument("--seconds", type=float, default=None); a = ap.parse_args()
    pairs = random_pairs(a.pairs, seed=a.seed); lm = LM.load(a.init) if a.init else LM(H=a.H); t0 = time.time(); r = train(lm, pairs, a.epochs, lr=a.lr, max_seconds=a.seconds)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); lm.save(a.out); print(r, f"{time.time() - t0:.0f}s", Path(a.out).stat().st_size // 1024, "KB")
