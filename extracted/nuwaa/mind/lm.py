# -*- coding: utf-8 -*-
"""A small NEURAL language model with real learned weights, pure numpy: runs on a phone CPU (Termux), needs no GPU and no PyTorch.
It is conditional: it writes a Python EXPRESSION token by token, given (a) the last C tokens it wrote and (b) a bag of the words of the task description.
It can GROW without forgetting: widen the hidden layer (new units start with zero output weights, so the function is unchanged) and add new tokens/words.
Whatever it writes is only a PROPOSAL: the verifier (safe_eval + sandbox + hidden cases) decides."""
import json, os, re
from pathlib import Path
import numpy as np

TOK = re.compile(r"\s+|[A-Za-z_]\w*|\d+|[^\w\s]")
PAD, BOS, EOS, UNK = "<pad>", "<bos>", "<eos>", "<unk>"
def code_tokens(s): return TOK.findall(s)
def word_tokens(s):
    from .vocab import words
    return [w for w in words(s) if w.isalnum()]

class LM:
    def __init__(self, toks=None, words=None, C=10, E=32, H=384, seed=0):
        self.C, self.E, self.H = C, E, H; self.rng = np.random.default_rng(seed)
        self.toks = toks or [PAD, BOS, EOS, UNK]; self.words = words or [PAD, UNK]
        V, Vp = len(self.toks), len(self.words); r = self.rng
        self.P = {"E": r.normal(0, .1, (V, E)), "W1": r.normal(0, (2 / (C * E)) ** .5, (C * E, H)), "Ep": r.normal(0, .1, (Vp, H)), "b1": np.zeros(H),
                  "W2": r.normal(0, (1 / H) ** .5, (H, V)), "b2": np.zeros(V)}
        self.P = {k: v.astype(np.float32) for k, v in self.P.items()}; self._index(); self.opt = None; self.steps = 0
    def _index(self): self.ti = {t: i for i, t in enumerate(self.toks)}; self.wi = {w: i for i, w in enumerate(self.words)}
    def n_params(self): return int(sum(v.size for v in self.P.values()))
    def nbytes(self): return self.n_params() * 4
    # ---- encoding ----
    def enc_code(self, s): return [self.ti.get(t, 3) for t in code_tokens(s)]
    def enc_words(self, s): return [self.wi.get(w, 1) for w in word_tokens(s)][:24] or [1]
    # ---- forward / backward ----
    def _fwd(self, X, PW):
        B = X.shape[0]; e = self.P["E"][X].reshape(B, -1); m = (PW > 0).astype(np.float32); n = np.maximum(m.sum(1, keepdims=True), 1)
        bag = (self.P["Ep"][PW] * m[:, :, None]).sum(1) / n
        h = np.tanh(e @ self.P["W1"] + bag + self.P["b1"]); return e, m, n, h, h @ self.P["W2"] + self.P["b2"]
    def loss(self, X, Y, PW):
        *_, lg = self._fwd(X, PW); lg = lg - lg.max(1, keepdims=True); lp = lg - np.log(np.exp(lg).sum(1, keepdims=True))
        return float(-lp[np.arange(len(Y)), Y].mean())
    def _step(self, X, Y, PW, lr):
        P = self.P; B = len(Y); e, m, n, h, lg = self._fwd(X, PW)
        lg = lg - lg.max(1, keepdims=True); p = np.exp(lg); p /= p.sum(1, keepdims=True); loss = float(-np.log(p[np.arange(B), Y] + 1e-9).mean())
        d = p; d[np.arange(B), Y] -= 1; d /= B
        g = {"W2": h.T @ d, "b2": d.sum(0)}; dh = (d @ P["W2"].T) * (1 - h * h)
        g["W1"] = e.T @ dh; g["b1"] = dh.sum(0); de = (dh @ P["W1"].T).reshape(B, self.C, self.E)
        gE = np.zeros_like(P["E"]); np.add.at(gE, X, de); g["E"] = gE
        gEp = np.zeros_like(P["Ep"]); np.add.at(gEp, PW, (dh / n)[:, None, :] * m[:, :, None]); g["Ep"] = gEp
        if self.opt is None: self.opt = {k: [np.zeros_like(v), np.zeros_like(v)] for k, v in P.items()}
        self.steps += 1; t = self.steps
        for k in P:
            mm, vv = self.opt[k]; mm *= .9; mm += .1 * g[k]; vv *= .999; vv += .001 * g[k] * g[k]
            P[k] -= (lr * (mm / (1 - .9 ** t)) / (np.sqrt(vv / (1 - .999 ** t)) + 1e-8)).astype(np.float32)
        return loss
    def fit(self, X, Y, EX, PWall, epochs=5, batch=512, lr=3e-3, seed=0, say=print, val=None, max_seconds=None):
        import time
        r = np.random.default_rng(seed); t0 = time.time(); n = len(Y)
        for ep in range(epochs):
            order = r.permutation(n); tot = 0.0; k = 0; cur = lr * (0.5 * (1 + np.cos(np.pi * ep / max(1, epochs))) * .9 + .1)
            for i in range(0, n, batch):
                b = order[i:i + batch]; tot += self._step(X[b], Y[b], PWall[EX[b]], cur); k += 1
            msg = f"epoch {ep + 1}/{epochs} train_loss {tot / k:.3f}" + (f" val_ppl {self.perplexity(*val):.2f}" if val else "") + f" ({time.time() - t0:.0f}s)"; say(msg)
            if max_seconds and time.time() - t0 > max_seconds: break
    def perplexity(self, X, Y, EX, PWall):
        tot = 0.0
        for i in range(0, len(Y), 2048): tot += self.loss(X[i:i + 2048], Y[i:i + 2048], PWall[EX[i:i + 2048]]) * len(Y[i:i + 2048])
        return float(np.exp(tot / max(1, len(Y))))
    # ---- sampling ----
    def sample(self, desc, n=1, temperature=.7, top_k=8, max_len=70, seed=0, prefix=""):
        r = np.random.default_rng(seed); pw = np.array([self.enc_words(desc) + [0] * (24 - len(self.enc_words(desc)))] * n, dtype=np.int64)
        ctx = np.full((n, self.C), 0, dtype=np.int64); ctx[:, -1] = 1; outs = [[] for _ in range(n)]; alive = np.ones(n, bool)
        for tkn in (self.enc_code(prefix) if prefix else []):
            ctx = np.concatenate([ctx[:, 1:], np.full((n, 1), tkn)], 1)
            for o in outs: o.append(tkn)
        for _ in range(max_len):
            *_, lg = self._fwd(ctx, pw); lg[:, :2] = -1e9; lg[:, 3] = -1e9; nxt = np.zeros(n, dtype=np.int64)
            for i in range(n):
                if not alive[i]: continue
                l = lg[i]
                if temperature <= 0: nxt[i] = int(l.argmax()); continue
                idx = np.argpartition(-l, min(top_k, len(l) - 1))[:top_k]; z = l[idx] / temperature; z = np.exp(z - z.max()); nxt[i] = int(r.choice(idx, p=z / z.sum()))
            for i in range(n):
                if alive[i]:
                    if nxt[i] == 2: alive[i] = False
                    else: outs[i].append(int(nxt[i]))
            ctx = np.concatenate([ctx[:, 1:], nxt[:, None]], 1)
            if not alive.any(): break
        return ["".join(self.toks[t] for t in o) for o in outs]
    # ---- growing ----
    def add_vocab(self, toks=(), words=()):
        nt = [t for t in dict.fromkeys(toks) if t not in self.ti]; nw = [w for w in dict.fromkeys(words) if w not in self.wi]
        r = self.rng
        if nt:
            self.P["E"] = np.vstack([self.P["E"], r.normal(0, .1, (len(nt), self.E)).astype(np.float32)])
            self.P["W2"] = np.hstack([self.P["W2"], np.zeros((self.H, len(nt)), np.float32)]); self.P["b2"] = np.concatenate([self.P["b2"], np.full(len(nt), -2, np.float32)])
            self.toks += nt
        if nw: self.P["Ep"] = np.vstack([self.P["Ep"], r.normal(0, .1, (len(nw), self.H)).astype(np.float32)]); self.words += nw
        self._index(); self.opt = None; return len(nt), len(nw)
    def widen(self, extra):
        """Net2Net-style growth: new hidden units get small random inputs but ZERO outputs, so predictions are unchanged until training uses them."""
        r = self.rng; P = self.P
        P["W1"] = np.hstack([P["W1"], r.normal(0, (2 / (self.C * self.E)) ** .5, (self.C * self.E, extra)).astype(np.float32)])
        P["Ep"] = np.hstack([P["Ep"], r.normal(0, .1, (P["Ep"].shape[0], extra)).astype(np.float32)]); P["b1"] = np.concatenate([P["b1"], np.zeros(extra, np.float32)])
        P["W2"] = np.vstack([P["W2"], np.zeros((extra, P["W2"].shape[1]), np.float32)]); self.H += extra; self.opt = None
    # ---- save / load (fp16 on disk = half the size; loaded back to fp32) ----
    def save(self, path):
        meta = json.dumps({"toks": self.toks, "words": self.words, "C": self.C, "E": self.E, "H": self.H, "steps": self.steps}, ensure_ascii=False)
        tmp = str(path) + ".tmp.npz"; np.savez_compressed(tmp, meta=np.frombuffer(meta.encode("utf-8"), np.uint8), **{k: v.astype(np.float16) for k, v in self.P.items()}); os.replace(tmp, path)
    @classmethod
    def load(cls, path):
        z = np.load(path); meta = json.loads(bytes(z["meta"]).decode("utf-8")); m = cls.__new__(cls)
        m.C, m.E, m.H = meta["C"], meta["E"], meta["H"]; m.toks, m.words = meta["toks"], meta["words"]; m.rng = np.random.default_rng(1)
        m.P = {k: z[k].astype(np.float32) for k in ("E", "W1", "Ep", "b1", "W2", "b2")}; m.steps = meta.get("steps", 0); m.opt = None; m._index(); return m

def build_dataset(lm, pairs, sort_words=True):
    """pairs = [(description, expression_source)] -> X (ctx), Y (next token), EX (example id per position), PW (prompt word ids per example)."""
    X, Y, EX, PW = [], [], [], []
    for k, (desc, src) in enumerate(pairs):
        toks = [1] + lm.enc_code(src) + [2]; ctx = [0] * (lm.C - 1) + [1]
        w = lm.enc_words(desc); PW.append(w + [0] * (24 - len(w)))
        for t in toks[1:]:
            X.append(ctx[-lm.C:]); Y.append(t); EX.append(k); ctx = ctx + [t]
    return np.array(X, np.int64), np.array(Y, np.int64), np.array(EX, np.int64), np.array(PW, np.int64)
