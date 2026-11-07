# -*- coding: utf-8 -*-
"""GPU training of the SAME model the app runs (the numpy GRULM), for the big sizes (10M .. 100M weights).
Steps (Colab: Runtime -> T4 GPU):
  1. python tools/scale_up.py --target 10000000 --out scale/nlm_10m_init.npz        (or take the file shipped in scale/)
  2. python tools/train_gru_torch.py --init scale/nlm_10m_init.npz --out weights/nlm_10m.npz --steps 20000 --bs 64
  3. python -c "from nuwaa.lm.gru import GRULM; open('android/app/src/main/assets/nlm2.bin','wb').write(GRULM.load('weights/nlm_10m.npz').to_bytes())"
More data = a smarter model: add your own jsonl pairs ({"user":..,"bot":..}) to data/, or plain text files with --text FILE (one training text per line).
SAFETY: at the start it compares its loss with the numpy model's loss on the same text and STOPS if they differ (so it can never silently train a
different network). It was written without a GPU to test on: that check is how you know it is right on your machine."""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import torch
import torch.nn.functional as F
from nuwaa.lm.gru import GRULM
from nuwaa.lm.corpus import all_pairs, fmt
from nuwaa.lm.pretrain_gru import COVER

def cell(gx, h, Wh):
    H = h.shape[1]
    rz = torch.sigmoid(gx[:, :2 * H] + h @ Wh[:, :2 * H]); r, z = rz[:, :H], rz[:, H:]
    n = torch.tanh(gx[:, 2 * H:] + (r * h) @ Wh[:, 2 * H:])
    return (1 - z) * h + z * n

def forward(P, x):
    """x: (B, T) token ids -> logits (B, T, V). The two GRU layers, the gate order [r | z | n] and the output layer are the ones of nuwaa.lm.gru."""
    B, T = x.shape; H = P["Wh1"].shape[0]
    gx1 = P["E"][x] @ P["Wx1"] + P["b1"]
    h1 = x.new_zeros((B, H), dtype=torch.float32); h2 = h1.clone(); outs = []
    for t in range(T):
        h1 = cell(gx1[:, t], h1, P["Wh1"])
        h2 = cell(h1 @ P["Wx2"] + P["b2"], h2, P["Wh2"])
        outs.append(h2)
    return torch.stack(outs, 1) @ P["Wo"] + P["bo"]

def bits(P, ids, dev):
    x = torch.tensor(ids[None, :-1], device=dev); y = torch.tensor(ids[None, 1:], device=dev)
    with torch.no_grad(): lg = forward(P, x)
    return F.cross_entropy(lg.reshape(-1, lg.shape[-1]), y.reshape(-1)).item() / math.log(2)

def save(lm, P, t, path):
    for k in lm.P: lm.P[k] = P[k].detach().cpu().numpy().astype(np.float32)
    lm.t = t; lm.save(path)

def main():
    try:
        from nuwaa.lm import hw; print(hw.report(), flush=True)
    except Exception: pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--init", required=True); ap.add_argument("--out", required=True); ap.add_argument("--data", default="data"); ap.add_argument("--text", default="")
    ap.add_argument("--steps", type=int, default=5000); ap.add_argument("--bs", type=int, default=64); ap.add_argument("--T", type=int, default=128)
    ap.add_argument("--lr", type=float, default=2e-3); ap.add_argument("--amp", action="store_true"); a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    lm = GRULM.load(a.init); lm.encode(COVER)
    pairs = all_pairs(a.data); texts = [fmt(u, b) for u, b in pairs]
    if a.text:      # lines made by tools/prepare_corpus.py: a pair is  س:<question>TAB ج:<answer>  (the TAB becomes the line end the model was trained with)
        texts += [(l.rstrip("\n").replace("\tج:", "\nج:", 1) + "\n") for l in open(a.text, encoding="utf-8") if l.strip()]
    cut = max(1, len(texts) // 20); held = "\n" + "".join(texts[-cut:]); train = "\n" + "".join(texts[:-cut])
    ids = lm.encode(train, grow=False); hid_ids = lm.encode(held, grow=False)[:4000]
    P = {k: torch.nn.Parameter(torch.tensor(v, device=dev)) for k, v in lm.P.items()}
    # --- self-check: this torch network must give the numpy model's loss on the same text, or we stop ---
    probe = lm.encode("س:مرحبا\nج:أهلا بك يا صديقي، كيف أساعدك؟\n", grow=False)
    ref, mine = lm.bpc(probe), bits(P, probe, dev)
    print(f"self-check: numpy model {ref:.4f} bits/char | this trainer {mine:.4f}")
    if abs(ref - mine) > 0.03: sys.exit("STOP: the torch network does not match the numpy model; nothing was trained.")
    opt = torch.optim.AdamW(P.values(), lr=a.lr, betas=(0.9, 0.99), weight_decay=0.0)
    best = bits(P, hid_ids, dev); print(f"{len(ids):,} training characters | held-out now {best:.4f} bits/char | device {dev}")
    t0 = time.time(); ema = None
    for step in range(1, a.steps + 1):
        lr = a.lr * min(1.0, step / 100) * (0.5 * (1 + math.cos(math.pi * step / a.steps)) * 0.9 + 0.1)
        for g in opt.param_groups: g["lr"] = lr
        st = np.random.randint(0, len(ids) - a.T - 2, a.bs); w = np.stack([ids[s:s + a.T + 1] for s in st])
        x = torch.tensor(w[:, :-1], device=dev); y = torch.tensor(w[:, 1:], device=dev)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=a.amp and dev == "cuda"):
            lg = forward(P, x)
        loss = F.cross_entropy(lg.float().reshape(-1, lg.shape[-1]), y.reshape(-1))
        opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(list(P.values()), 1.0); opt.step()
        b = loss.item() / math.log(2); ema = b if ema is None else 0.98 * ema + 0.02 * b
        if step % 100 == 0: print(f"step {step}/{a.steps} train {ema:.3f} bits/char lr {lr:.5f} ({time.time() - t0:.0f}s)", flush=True)
        if step % 500 == 0 or step == a.steps:
            h = bits(P, hid_ids, dev)
            if h < best: best = h; save(lm, P, step, a.out); print(f"  held-out {h:.4f}  <- best, saved to {a.out}", flush=True)
            else: print(f"  held-out {h:.4f} (best {best:.4f})", flush=True)
    print("done. best held-out", round(best, 4), "bits/char (lower is better); the previous best was the starting file's score")

if __name__ == "__main__": main()
