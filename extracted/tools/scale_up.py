# -*- coding: utf-8 -*-
"""Makes the model BIGGER without losing anything it knows: the new model starts exactly where the old one stands (GRULM.widened), then needs training
to use the extra room (tools/train_gru_torch.py on a GPU, or nuwaa.lm.pretrain_gru --init on a CPU).
  python tools/scale_up.py --target 10000000 --out scale/nlm_10m_init.npz
  python tools/scale_up.py --target 100000000 --bench            # only measure: no file written
Reports parameters, file/RAM size and the measured speed of one character on THIS machine."""
import argparse, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from nuwaa.lm.gru import GRULM, VMAX

def count(E, H, V=VMAX):
    return V * E + (E * 3 * H + H * 3 * H + 3 * H) + (H * 3 * H + H * 3 * H + 3 * H) + H * V + V

def pick_hidden(target, E):
    H = 64
    while count(E, H + 32) <= target: H += 32
    return H

def main():
    try:
        from nuwaa.lm import hw; print(hw.report(), flush=True)
    except Exception: pass

    ap = argparse.ArgumentParser(); ap.add_argument("--weights", default="weights/nlm2.npz"); ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--emb", type=int, default=0); ap.add_argument("--out", default=""); ap.add_argument("--bench", action="store_true"); ap.add_argument("--dry", action="store_true", help="only the numbers, nothing is built (for sizes that do not fit in memory here)"); a = ap.parse_args()
    if a.dry:
        E = a.emb or 128; H = pick_hidden(a.target, E); n = count(E, H)
        print(f"emb {E} hid {H} params {n:,} | weights {n * 4 / 1e6:.0f} MB float32 ({n * 2 / 1e6:.0f} MB half) | Adam training state {n * 12 / 1e6:.0f} MB | MACs per character {2 * (3 * H * (E + H) + 6 * H * H) / 1e6:.0f} M")
        return
    old = GRULM.load(a.weights)
    E = a.emb or max(old.E, 128 if a.target >= 8_000_000 else 64)
    H = max(old.H, pick_hidden(a.target, E))
    t0 = time.time(); new = old.widened(E, H); n = new.n_params()
    print(f"old: emb {old.E} hid {old.H} params {old.n_params():,}\nnew: emb {E} hid {H} params {n:,} (target {a.target:,}) built in {time.time() - t0:.1f}s")
    print(f"file/RAM of the weights: {n * 4 / 1e6:.0f} MB float32 | with Adam training state: {n * 12 / 1e6:.0f} MB | MACs per character: {2 * (3 * H * (E + H) + 3 * H * 2 * H) / 1e6:.0f} M")
    txt = "س:مرحبا\nج:أهلا بك.\n"; ids = old.encode(txt, grow=False)
    print("same behaviour as the old model at the start: bits/char old %.4f new %.4f" % (old.bpc(ids), new.bpc(ids)))
    st = new.zero_state(1); steps = 20 if n < 30_000_000 else 6
    t0 = time.time(); cid = 5
    for _ in range(steps): p, st = new.step_char(cid, st)
    ms = (time.time() - t0) / steps * 1000
    print(f"speed on this machine (one CPU core, numpy): {ms:.1f} ms per character -> a 300-character reply ~ {ms * 300 / 1000:.0f} s")
    if a.out and not a.bench:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True); new.save(a.out); print("saved", a.out, f"({os.path.getsize(a.out) / 1e6:.0f} MB)")

if __name__ == "__main__": main()
