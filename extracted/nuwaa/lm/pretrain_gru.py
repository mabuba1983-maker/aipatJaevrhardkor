# -*- coding: utf-8 -*-
"""Pretrain the recurrent model on the project's own data:
  python -m nuwaa.lm.pretrain_gru [--out weights/nlm2.npz] [--bin android/app/src/main/assets/nlm2.bin] [--epochs 60]
Pairs are shuffled again every epoch and joined into one long stream, so the hidden state learns to carry a conversation and to start a new one.
Keeps the epoch with the best loss on held-out pairs (memorising does not win); the held-out pairs are then trained on briefly too."""
import argparse, copy, sys, time
import numpy as np
from .gru import GRULM
from .corpus import all_pairs, fmt
import string
COVER = "".join(chr(c) for c in range(0x621, 0x64B)) + "".join(chr(c) for c in range(0x64B, 0x653)) + string.printable[:95] + "،؛؟«»¶…—\u2192\u2190\u2022✓⚠📎"

import string
# every printable ASCII char, all Arabic letters, diacritics and Arabic digits are in the vocabulary, so user input is never turned into "?"
COVER = string.printable.replace("\x0b", "").replace("\x0c", "").replace("\r", "") + "".join(chr(c) for c in range(0x0621, 0x064B)) + "".join(chr(c) for c in range(0x064B, 0x0653)) + "٠١٢٣٤٥٦٧٨٩،؛؟«»¶ـ"

# every letter a user can type must be in the vocabulary (otherwise it becomes '?'): ASCII, the whole Arabic letter block, marks, digits, punctuation
COVER = "".join(chr(c) for c in range(32, 127)) + "".join(chr(c) for c in range(0x621, 0x653)) + "٠١٢٣٤٥٦٧٨٩ـ،؛؟«»¶×÷•·←→✓⚠📎“”‘’…—–\n"

def main(argv=None):
    try:
        from nuwaa.lm import hw; print(hw.report(), flush=True)
    except Exception: pass

    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data"); ap.add_argument("--out", default="weights/nlm2.npz"); ap.add_argument("--bin", default="")
    ap.add_argument("--epochs", type=int, default=60); ap.add_argument("--hid", type=int, default=256); ap.add_argument("--emb", type=int, default=48)
    ap.add_argument("--seconds", type=int, default=3000); ap.add_argument("--lr", type=float, default=3e-3); ap.add_argument("--init", default=""); ap.add_argument("--text", default="", help="extra training lines made by tools/prepare_corpus.py (programming + Arabic only)")
    a = ap.parse_args(argv); P = all_pairs(a.data); r = np.random.RandomState(1); idx = r.permutation(len(P)); nh = max(12, len(P) // 20)
    hold = [P[i] for i in idx[:nh]]; tr = [P[i] for i in idx[nh:]]
    m = GRULM.load(a.init) if a.init else GRULM(emb=a.emb, hid=a.hid, seed=0); m.encode(COVER); m.encode(COVER); m.encode(COVER); m.encode("".join(fmt(*p) for p in P)); hids = m.encode("".join(fmt(*p) for p in hold), grow=False)
    print(f"pairs {len(P)} (held-out {len(hold)}) params {m.n_params()} vocab {m.nv}", flush=True)
    extra = [l.rstrip("\n").replace("\tج:", "\nج:", 1) + "\n" for l in open(a.text, encoding="utf-8") if l.strip()] if a.text else []
    texts = [fmt(*p) for p in tr] + extra
    best, state, t0 = 9e9, None, time.time(); E = a.epochs
    for ep in range(E):
        lr = a.lr * (0.5 * (1 + np.cos(np.pi * ep / E)) * 0.9 + 0.1)          # cosine decay
        order = np.random.RandomState(100 + ep).permutation(len(texts)); ids = m.encode("".join(texts[i] for i in order), grow=False)
        loss = m.train_stream(ids, B=32, T=96, epochs=1, lr=lr, seed=ep); h = m.bpc(hids)
        print(f"epoch {ep + 1}/{E} lr {lr:.4f} train bits/char {loss / np.log(2):.3f} held-out bits/char {h:.3f} ({time.time() - t0:.0f}s)", flush=True)
        if h < best: best, state = h, (copy.deepcopy(m.P), m.t); m.save(a.out)                    # a checkpoint of the best epoch so far: an interrupted run loses nothing
        if time.time() - t0 > a.seconds: print("time budget reached", flush=True); break
    m.P, m.t = state; print(f"best held-out bits/char {best:.3f}", flush=True)
    allids = m.encode("".join(fmt(*p) for p in P), grow=False)
    for k in range(3): m.train_stream(allids, B=32, T=96, epochs=1, lr=3e-4, seed=900 + k)          # the held-out pairs are data too: a short pass at the end
    print(f"final bits/char over all data {m.bpc(allids):.3f}", flush=True)
    m.save(a.out)
    if a.bin:
        with open(a.bin, "wb") as f: f.write(m.to_bytes())
    print("saved", a.out, a.bin, flush=True)

if __name__ == "__main__": main()
