# -*- coding: utf-8 -*-
"""Semantic (الفهم الدلالي): the meaning engine of Nuwaa, used by Fahm (conversation/understand.py) for questions it has not seen worded this way. Built from scratch, numpy only: no PyTorch, no GPU, no downloaded model.
It LEARNS from data/ (a few seconds on CPU) and keeps three views of every sentence:
  1. meaning vectors  - word vectors learned from the corpus itself (co-occurrence -> PPMI -> SVD), so "اجمع" and "مجموع" land close together
  2. spelling vectors - hashed character trigrams, so typos and dialect spellings still match
  3. coverage         - how much of the question's content the match explains (stops "python" alone from matching anything)
It answers only when confident AND clearly ahead of the runner-up; otherwise it says so (the caller then asks or falls back)."""
import math
import numpy as np
from ..memory.kb import tokens, norm, LANGS

DIM, HASH = 64, 4096
KNOWN_POWER = 1.0   # score is multiplied by (share of the question's words the engine knows) ** KNOWN_POWER: words it has never seen count against it
WEIGHTS = (0.40, 0.08, 0.14, 0.38)   # meaning, spelling, coverage-of-question-phrasing, coverage-in-answer

def _trigrams(s):
    s = " " + " ".join(norm(s).split()) + " "
    return [s[i:i + 3] for i in range(max(1, len(s) - 2))]

def _hash(g): return (sum((ord(c) * 131 ** i) for i, c in enumerate(g)) % HASH)   # deterministic across runs (python's hash() is salted)

class Semantic:
    def __init__(self, dim=DIM):
        self.dim = dim; self.rows = []; self.ready = False

    # ---------- training ----------
    def fit(self, items):
        """items: iterable of (question_phrasings: list[str], answer: str, payload). Returns self."""
        self.rows, docs, self.ans = [], [], []
        for qs, a, payload in items:
            qt = [tokens(q) for q in qs]
            at = tokens(a[:600])
            docs.append(set().union(*qt) | at)
            for q, t in zip(qs, qt): self.rows.append((q, t, payload)); self.ans.append(at)
        df = {}
        for d in docs:
            for t in d: df[t] = df.get(t, 0) + 1
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n, V = len(docs), len(self.vocab)
        self.idf = {t: math.log(1 + n / (1 + c)) for t, c in df.items()}
        self.max_idf = math.log(1 + n)
        # word-word co-occurrence over documents -> PPMI -> truncated SVD = learned word meaning
        C = np.zeros((V, V), dtype=np.float32)
        for d in docs:
            ids = [self.vocab[t] for t in d]
            if len(ids) > 1: C[np.ix_(ids, ids)] += 1
        np.fill_diagonal(C, 0)
        tot = C.sum() or 1.0; r = C.sum(1, keepdims=True); c = C.sum(0, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            P = np.maximum(np.log((C * tot) / (r * c + 1e-9) + 1e-9), 0)
        P[~np.isfinite(P)] = 0
        k = min(self.dim, V - 1) if V > 1 else 1
        U, S, _ = np.linalg.svd(P, full_matrices=False)
        W = U[:, :k] * np.sqrt(S[:k])
        W /= (np.linalg.norm(W, axis=1, keepdims=True) + 1e-9)
        self.W = W.astype(np.float32)
        # char-trigram document frequency
        gdf = np.zeros(HASH, dtype=np.float32)
        for q, _, _ in self.rows:
            for h in {_hash(g) for g in _trigrams(q)}: gdf[h] += 1
        self.gidf = np.log(1 + len(self.rows) / (1 + gdf)).astype(np.float32)
        self.S = np.stack([self._sem(t) for _, t, _ in self.rows]) if self.rows else np.zeros((0, k), np.float32)
        self.G = np.stack([self._chr(q) for q, _, _ in self.rows]) if self.rows else np.zeros((0, HASH), np.float32)
        self.ready = True; return self

    # ---------- encoding ----------
    def _sem(self, toks):
        v = np.zeros(self.W.shape[1], dtype=np.float32)
        for t in toks:
            i = self.vocab.get(t)
            if i is not None: v += self.idf[t] * self.W[i]
        n = np.linalg.norm(v); return v / n if n > 0 else v
    def _chr(self, text):
        v = np.zeros(HASH, dtype=np.float32)
        for g in _trigrams(text): v[_hash(g)] += 1
        v = np.log1p(v) * self.gidf; n = np.linalg.norm(v); return v / n if n > 0 else v
    def _coverage(self, qt, rt):
        """share of the question's information (idf weight) that the matched phrasing contains, in either direction."""
        w = lambda ts: sum(self.idf.get(t, self.max_idf) for t in ts) or 1.0
        inter = qt & rt
        wi = sum(self.idf.get(t, 0) for t in inter)
        pq, pp = wi / w(qt), wi / w(rt)
        return (2 * pq * pp / (pq + pp)) if pq + pp else 0.0

    # ---------- understanding ----------
    def features(self, text):
        """per-phrasing feature matrix [meaning, spelling, coverage, answer-coverage] (used for scoring and for tuning)."""
        qt = tokens(text)
        sem = self.S @ self._sem(qt); chr_ = self.G @ self._chr(text)
        ql = qt & LANGS; wq = sum(self.idf.get(t, self.max_idf) for t in qt) or 1.0
        F = np.zeros((len(self.rows), 4), dtype=np.float32); pen = np.ones(len(self.rows), dtype=np.float32)
        for i, (q, rt, payload) in enumerate(self.rows):
            rl = rt & LANGS
            if ql and rl and not (ql & rl): pen[i] = 0.5          # asked about python, this phrasing is about css: not the same thing
            F[i] = (max(sem[i], 0), max(chr_[i], 0), self._coverage(qt, rt), sum(self.idf.get(t, 0) for t in qt & self.ans[i]) / wq)
        kn = sum(self.idf.get(t, 0) for t in qt) / wq
        return F, pen, kn

    def understand(self, text, k=3):
        """-> list of (score, payload, matched_phrasing), best first, one entry per payload."""
        if not self.ready or not self.rows: return []
        if not text.strip(): return []
        F, pen, kn = self.features(text); sc = (F @ np.array(WEIGHTS, dtype=np.float32)) * pen * (kn ** KNOWN_POWER)
        res = {}
        for i, (q, rt, payload) in enumerate(self.rows):
            key = id(payload)
            if key not in res or sc[i] > res[key][0]: res[key] = (float(sc[i]), payload, q)
        return sorted(res.values(), key=lambda x: -x[0])[:k]

    def answer(self, text, accept=0.50, margin=0.06):   # tuned on 3 held-out folds: answers ~58% of unseen phrasings at ~80% precision
        """-> (payload, score, status) with status 'sure' | 'unsure' | 'none'. Never guesses: the caller decides what to do when not sure."""
        r = self.understand(text, 2)
        if not r: return None, 0.0, "none"
        best = r[0]; gap = best[0] - (r[1][0] if len(r) > 1 else 0.0)
        if best[0] >= accept and gap >= margin: return best[1], best[0], "sure"
        return best[1], best[0], "unsure"
