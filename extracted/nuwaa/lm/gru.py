# -*- coding: utf-8 -*-
"""GRULM: a character-level RECURRENT language model written from scratch in numpy (no fixed window: the 24-character limit is gone).
 * neural part: embedding -> GRU layer 1 -> GRU layer 2 -> softmax over characters. The hidden state is carried from one character to the next,
   so everything said so far in a conversation can influence the next character (a recurrent state is a compressed memory: it fades with very
   long text, which is why the n-gram memories below exist too).
 * long-term memory  (NGram `long`):  counts learned from what the user says; saved on the phone; survives conversations.
 * short-term memory (NGram `short`): lives in a Session only; the Session (hidden state + this memory) is dropped when the conversation ends.
 * Reply = the model WRITES it character by character. There is no confidence gate and no canned phrase: it always answers.
HONEST LIMIT: small model, small data. It writes rough Arabic until it has seen much more text."""
import json, re, time
from collections import defaultdict, Counter
import numpy as np

VMAX = 256
NL = "\n"
MAGIC = b"NLM2"


class NGram:
    MAXO = 8
    def __init__(self): self.t = defaultdict(Counter); self.n = 0
    def add(self, text):
        text = NL + text + NL
        for i in range(1, len(text)):
            for o in range(1, self.MAXO + 1):
                if i - o < 0: break
                self.t[text[i - o:i]][text[i]] += 1
        self.n += len(text)
    def dist(self, ctx, min_o=1):
        for o in range(min(self.MAXO, len(ctx)), min_o - 1, -1):
            c = self.t.get(ctx[-o:])
            if c: return o, c
        return 0, None


def _sig(x): return 1.0 / (1.0 + np.exp(-x))


class GRULM:
    def __init__(self, emb=48, hid=256, seed=0, adam=True):
        self.E, self.H = emb, hid
        r = np.random.RandomState(seed); H = hid
        w = lambda a, b, s=1.0: (r.randn(a, b) * s / np.sqrt(a)).astype(np.float32)
        z = lambda n: np.zeros(n, np.float32)
        self.P = dict(E=(r.randn(VMAX, emb) * 0.1).astype(np.float32),
                      Wx1=w(emb, 3 * H), Wh1=w(H, 3 * H), b1=z(3 * H),
                      Wx2=w(H, 3 * H), Wh2=w(H, 3 * H), b2=z(3 * H),
                      Wo=w(H, VMAX, 0.5), bo=z(VMAX))
        self.vocab = {"\0": 0, "?": 1}; self.chars = ["\0", "?"]
        self.m = {k: np.zeros_like(v) for k, v in self.P.items()} if adam else None; self.v = {k: np.zeros_like(v) for k, v in self.P.items()} if adam else None   # adam=False: a 2 GB model is built without 3x the memory
        self.t = 0; self.long = NGram()

    # ---------- vocabulary ----------
    @property
    def nv(self): return len(self.chars)
    def n_params(self): return int(sum(v.size for v in self.P.values()))
    def cid(self, c, grow=True):
        i = self.vocab.get(c)
        if i is not None: return i
        if not grow or len(self.chars) >= VMAX: return 1
        self.vocab[c] = len(self.chars); self.chars.append(c); return self.vocab[c]
    def encode(self, text, grow=True): return np.array([self.cid(c, grow) for c in text], np.int64)

    # ---------- GRU cell ----------
    def zero_state(self, B=1): return (np.zeros((B, self.H), np.float32), np.zeros((B, self.H), np.float32))

    def _cell(self, gx, h, Wh):
        H = self.H
        rz = _sig(gx[:, :2 * H] + h @ Wh[:, :2 * H]); r, z = rz[:, :H], rz[:, H:]
        rh = r * h; n = np.tanh(gx[:, 2 * H:] + rh @ Wh[:, 2 * H:])
        return (1 - z) * h + z * n, (r, z, n, h, rh)

    def _cell_bwd(self, dhn, c, Wh, dWh):
        H = self.H; r, z, n, h, rh = c
        dz = dhn * (n - h); dn = dhn * z; dh = dhn * (1 - z)
        dan = dn * (1 - n * n)
        dWh[:, 2 * H:] += rh.T @ dan
        drh = dan @ Wh[:, 2 * H:].T
        dr = drh * h; dh = dh + drh * r
        dg = np.concatenate([dr * r * (1 - r), dz * z * (1 - z)], 1)
        dWh[:, :2 * H] += h.T @ dg
        dh = dh + dg @ Wh[:, :2 * H].T
        return np.concatenate([dg, dan], 1), dh

    # ---------- sequence forward / backward (training) ----------
    def forward(self, X, state):
        P = self.P; B, T = X.shape; H = self.H
        e = P["E"][X]; gx1 = e @ P["Wx1"] + P["b1"]
        h1, h2 = state; dt = P["Wo"].dtype; H1 = np.empty((B, T, H), dt); H2 = np.empty((B, T, H), dt); c1s = []; c2s = []
        for t in range(T):
            h1, c1 = self._cell(gx1[:, t], h1, P["Wh1"])
            h2, c2 = self._cell(h1 @ P["Wx2"] + P["b2"], h2, P["Wh2"])
            H1[:, t] = h1; H2[:, t] = h2; c1s.append(c1); c2s.append(c2)
        lg = H2 @ P["Wo"] + P["bo"]; lg[..., self.nv:] = -1e9
        lg = lg - lg.max(-1, keepdims=True); p = np.exp(lg); p /= p.sum(-1, keepdims=True)
        return p, (X, e, H1, H2, c1s, c2s), (h1, h2)

    def loss_grads(self, X, Y, state):
        p, (X, e, H1, H2, c1s, c2s), st = self.forward(X, state); P = self.P; B, T = X.shape; H = self.H
        n = B * T; loss = float(-np.log(np.take_along_axis(p, Y[..., None], -1) + 1e-9).mean())
        d = p; np.put_along_axis(d, Y[..., None], np.take_along_axis(d, Y[..., None], -1) - 1, -1); d /= n; d[..., self.nv:] = 0
        g = {k: np.zeros_like(v) for k, v in P.items()}
        g["Wo"] = H2.reshape(n, H).T @ d.reshape(n, -1); g["bo"] = d.reshape(n, -1).sum(0)
        dH2 = d @ P["Wo"].T
        dt = P["Wo"].dtype; dgx1 = np.empty((B, T, 3 * H), dt); dgx2 = np.empty((B, T, 3 * H), dt)
        dh1c = np.zeros((B, H), dt); dh2c = np.zeros((B, H), dt)
        for t in range(T - 1, -1, -1):
            dgx2[:, t], dh2c = self._cell_bwd(dH2[:, t] + dh2c, c2s[t], P["Wh2"], g["Wh2"])
            dgx1[:, t], dh1c = self._cell_bwd(dgx2[:, t] @ P["Wx2"].T + dh1c, c1s[t], P["Wh1"], g["Wh1"])
        g["Wx2"] = H1.reshape(n, H).T @ dgx2.reshape(n, -1); g["b2"] = dgx2.reshape(n, -1).sum(0)
        g["Wx1"] = e.reshape(n, -1).T @ dgx1.reshape(n, -1); g["b1"] = dgx1.reshape(n, -1).sum(0)
        np.add.at(g["E"], X, dgx1 @ P["Wx1"].T)
        return loss, g, st

    def adam(self, g, lr, clip=1.0):
        nrm = float(np.sqrt(sum((v ** 2).sum() for v in g.values())))
        if nrm > clip: g = {k: v / nrm for k, v in g.items()}
        if self.m is None: self.m = {k: np.zeros_like(v) for k, v in self.P.items()}; self.v = {k: np.zeros_like(v) for k, v in self.P.items()}
        self.t += 1; b1, b2 = 0.9, 0.999
        for k in self.P:
            self.m[k] = b1 * self.m[k] + (1 - b1) * g[k]; self.v[k] = b2 * self.v[k] + (1 - b2) * g[k] ** 2
            self.P[k] -= lr * (self.m[k] / (1 - b1 ** self.t)) / (np.sqrt(self.v[k] / (1 - b2 ** self.t)) + 1e-8)

    def train_stream(self, ids, B=32, T=96, epochs=1, lr=3e-3, reset=0.12, seed=0, say=None, max_seconds=None):
        """Stateful truncated BPTT: the text is cut into B parallel streams, the hidden state is carried between chunks (sometimes reset to
        zero, so the model also learns to start a fresh conversation)."""
        r = np.random.RandomState(seed); L = (len(ids) - 1) // B
        if L < 2: return 0.0
        X = ids[:L * B].reshape(B, L); Y = ids[1:L * B + 1].reshape(B, L); t0 = time.time(); last = 0.0
        for ep in range(epochs):
            st = self.zero_state(B); tot = 0.0; n = 0
            off = int(r.randint(0, T))
            for i in range(off, L - 1, T):
                x = X[:, i:i + T]; y = Y[:, i:i + T]
                if x.shape[1] < 2: break
                loss, g, st = self.loss_grads(x, y, st); self.adam(g, lr)
                tot += loss * x.shape[1]; n += x.shape[1]
                mask = (r.rand(B) < reset)[:, None]
                st = tuple(np.where(mask, 0, s).astype(np.float32) for s in st)
                if max_seconds and time.time() - t0 > max_seconds: break
            last = tot / max(n, 1)
            if say: say(f"epoch {ep + 1}/{epochs} loss {last:.3f} bits/char {last / np.log(2):.3f} ({time.time() - t0:.0f}s)")
            if max_seconds and time.time() - t0 > max_seconds: break
        return last

    def bpc(self, ids, T=128):
        """Bits per character with ONE long state over the whole text (this is what unbounded context means)."""
        if len(ids) < 3: return 0.0
        st = self.zero_state(1); tot = 0.0; n = 0
        for i in range(0, len(ids) - 1, T):
            x = ids[None, i:i + T]; y = ids[None, i + 1:i + 1 + T]; x = x[:, :y.shape[1]]
            if x.shape[1] == 0: break
            p, _, st = self.forward(x, st)
            tot += float(-np.log(np.take_along_axis(p, y[..., None], -1) + 1e-9).sum()); n += y.shape[1]
        return tot / n / np.log(2)

    # ---------- one-character inference ----------
    def step_char(self, cid, state):
        P = self.P; h1, h2 = state
        h1, _ = self._cell(P["E"][[cid]] @ P["Wx1"] + P["b1"], h1, P["Wh1"])
        h2, _ = self._cell(h1 @ P["Wx2"] + P["b2"], h2, P["Wh2"])
        lg = h2 @ P["Wo"][:, :self.nv] + P["bo"][:self.nv]; lg = lg[0] - lg.max(); p = np.exp(lg); p /= p.sum()
        return p, (h1, h2)

    # ---------- learning from what the user says ----------
    def observe(self, text, steps=0, lr=1e-3):
        """Long-term memory at once (n-grams). The weights are NOT touched here any more: a few gradient steps on every raw message made the
        model collapse and echo what the user had said (the repetition bug). Weights change only in develop(), which rehearses old data and rolls back."""
        self.long.add(text)
        ids = self.encode("س:" + text + NL)
        if steps <= 0 or len(ids) < 4: return
        for _ in range(steps):                                                  # only when a caller asks for it explicitly
            _, g, _ = self.loss_grads(ids[None, :-1], ids[None, 1:], self.zero_state(1)); self.adam(g, lr)

    def observe_pair(self, q, a, steps=3, lr=1e-3):
        """Learn one question/answer pair in the same layout used in pretraining (admin teaching through the API)."""
        t = "س:" + q.replace("\n", " ¶ ") + NL + "ج:" + a.replace("\n", "¶") + NL
        self.long.add("س:" + q); self.long.add("ج:" + a)
        ids = self.encode(t)
        for _ in range(steps):
            _, g, _ = self.loss_grads(ids[None, :-1], ids[None, 1:], self.zero_state(1)); self.adam(g, lr)

    def develop(self, texts, epochs=3, lr=3e-4, T=96, rehearse=None):
        """Self-development on everything heard. `rehearse` = (user, bot) pairs of the original training data, mixed in so nothing already
        known is forgotten. Returns (bits/char before, after) on the heard text; the weights are rolled back if the heard text did not get
        better OR the rehearsal text got worse by more than 3 percent."""
        heard = "".join("س:" + t + NL for t in texts)
        reh = "".join("س:" + u.replace(NL, " ¶ ") + NL + "ج:" + b.replace(NL, "¶") + NL for u, b in (rehearse or []))
        ids = self.encode(heard)
        if len(ids) < 8: return 0.0, 0.0
        rids = self.encode(reh, grow=False) if reh else None
        before = self.bpc(ids); rbefore = self.bpc(rids) if rids is not None and len(rids) > 8 else None
        snap = {k: v.copy() for k, v in self.P.items()}
        mix = self.encode(heard + reh, grow=False) if reh else ids
        self.train_stream(mix, B=min(16, max(1, len(mix) // (2 * T))), T=T, epochs=epochs, lr=lr, seed=7)
        after = self.bpc(ids); rafter = self.bpc(rids) if rbefore is not None else None
        if after > before or (rbefore is not None and rafter > rbefore * 1.03):
            for k in self.P: self.P[k][...] = snap[k]
            return before, before
        return before, after

    # ---------- files ----------
    def widened(self, emb, hid, seed=1):
        """A bigger model that starts EXACTLY where this one stands: the old weights sit in the corner, every weight that leaves a new unit is zero
        (so the new units change nothing at first), every weight that enters a new unit is random (so they can learn). Training then uses the extra room."""
        E0, H0, E1, H1 = self.E, self.H, emb, hid
        assert E1 >= E0 and H1 >= H0
        n = GRULM(E1, H1, seed, adam=False); o = self.P; N = n.P
        N["E"][:, :E0] = o["E"]
        def put(name, r0):
            for g in range(3):
                cn = slice(g * H1, g * H1 + H0); co = slice(g * H0, (g + 1) * H0)
                N[name][:, cn] = 0; N[name][:r0, cn] = o[name][:, co]
        put("Wx1", E0); put("Wh1", H0); put("Wx2", H0); put("Wh2", H0)
        for b in ("b1", "b2"):
            N[b][:] = 0
            for g in range(3): N[b][g * H1:g * H1 + H0] = o[b][g * H0:(g + 1) * H0]
        N["Wo"][:] = 0; N["Wo"][:H0] = o["Wo"]; N["bo"][:] = o["bo"]
        n.chars = list(self.chars); n.vocab = dict(self.vocab); n.long = self.long; n.t = 0
        return n

    def save(self, path, fp16=False):
        """fp16=True stores the weights in half precision: half the file (a 2 GB model becomes a 1 GB file); loading converts back to float32."""
        np.savez_compressed(path, **{"P_" + k: (v.astype(np.float16) if fp16 else v) for k, v in self.P.items()}, chars=np.array(json.dumps(self.chars)),
                            cfg=np.array(json.dumps([self.E, self.H, self.t])))
    @classmethod
    def load(cls, path):
        z = np.load(path, allow_pickle=False); e, h, t = json.loads(str(z["cfg"])); m = cls(e, h, adam=False)
        for k in m.P: m.P[k] = z["P_" + k].astype(np.float32)
        m.chars = json.loads(str(z["chars"])); m.vocab = {c: i for i, c in enumerate(m.chars)}; m.t = int(t)
        return m

    def to_bytes(self):
        """NLM2 for the phone: magic, int32 E H V, int32 len(chars json), chars json (UTF-8), then float32 little-endian:
        E[V,E] Wx1[E,3H] Wh1[H,3H] b1[3H] Wx2[H,3H] Wh2[H,3H] b2[3H] Wo[H,V] bo[V]."""
        import struct
        V = self.nv; ch = json.dumps(self.chars, ensure_ascii=False).encode("utf-8"); P = self.P
        out = [MAGIC, struct.pack("<iii", self.E, self.H, V), struct.pack("<i", len(ch)), ch]
        for a in (P["E"][:V], P["Wx1"], P["Wh1"], P["b1"], P["Wx2"], P["Wh2"], P["b2"], P["Wo"][:, :V], P["bo"][:V]):
            out.append(np.ascontiguousarray(a, dtype="<f4").tobytes())
        return b"".join(out)
    @classmethod
    def from_bytes(cls, b):
        import struct
        assert b[:4] == MAGIC, "not an NLM2 file"
        e, h, V = struct.unpack_from("<iii", b, 4); (n,) = struct.unpack_from("<i", b, 16); chars = json.loads(b[20:20 + n].decode("utf-8")); o = 20 + n
        m = cls(e, h, adam=False)
        def take(shape):
            nonlocal o
            k = int(np.prod(shape)); a = np.frombuffer(b, "<f4", k, o).reshape(shape).astype(np.float32).copy(); o += 4 * k; return a
        m.chars = chars; m.vocab = {c: i for i, c in enumerate(chars)}
        m.P["E"][:V] = take((V, e))
        for k, shp in (("Wx1", (e, 3 * h)), ("Wh1", (h, 3 * h)), ("b1", (3 * h,)), ("Wx2", (h, 3 * h)), ("Wh2", (h, 3 * h)), ("b2", (3 * h,))): m.P[k] = take(shp)
        m.P["Wo"][:, :V] = take((h, V)); m.P["bo"][:V] = take((V,))
        return m


class Session:
    """One conversation. Hidden state + short-term memory live here and nowhere else: when the conversation ends, drop the Session
    (what the user said has already been learned into the long-term memory by lm.observe)."""
    def __init__(self, lm, seed=None):
        self.lm = lm; self.state = lm.zero_state(1); self.short = NGram(); self.text = ""; self.rng = np.random.RandomState(seed)
        self.p = None; self.replies = []; self._feed(NL)                                # every pair in training follows a line end: a fresh conversation starts the same way
    def _feed(self, s):
        for ch in s:
            self.p, self.state = self.lm.step_char(self.lm.cid(ch, False), self.state); self.text += ch
    MIN_ORDER = 4          # a memory may only speak when it matches at least 4 characters of context: it can then complete a word or fact
                           # but can never hijack the START of a reply (that is what made the model echo old messages)
    def _mix(self, p, mem_gain, short_gain):
        lm = self.lm; p = p.copy()
        for mem, gain in ((lm.long, mem_gain), (self.short, short_gain)):
            if not mem.n or gain <= 0: continue
            o, cnt = mem.dist(self.text, self.MIN_ORDER)
            if not cnt: continue
            tot = sum(cnt.values()); lam = gain * tot / (tot + 0.1) * min(1.0, (o - self.MIN_ORDER + 1) / 4.0); q = np.zeros_like(p)
            for ch, k in cnt.items(): q[lm.cid(ch, False)] += k / tot
            p = (1 - lam) * p + lam * q
        return p
    NG_SELF = 10           # inside one reply, no 10-character piece may be written twice
    NG_PREV = 8            # against earlier replies of this conversation: no 8-character piece (unless the user asked the same thing again)
    @staticmethod
    def _norm(t): return " ".join(t.split()).strip()
    def _grams(self, text, n):
        return {text[i:i + n] for i in range(len(text) - n + 1)} if len(text) >= n else set()
    @staticmethod
    def dedupe(text):
        """Drops a sentence/line that repeats one already written; collapses a tail that loops."""
        parts = re.split(r"(?<=[.!?؟\n])", text); seen = set(); out = []
        for part in parts:
            k = part.strip()
            if len(k) >= 6 and k in seen: continue
            seen.add(k); out.append(part)
        return "".join(out).strip()
    @staticmethod
    def copy_source(u):
        """The request, prepared for copying: list commas become line ends (a file lists items one per line), «باسم x.py» becomes the file-block opener."""
        return re.sub(r"(\x01ملف:)+", "\x01ملف:", re.sub(r"\s*،\s*", "\n", u).replace("باسم ", "\x01ملف:").replace("مجلد ", "\x01ملف:"))          # \x01 stands for the opener: the closer «<<نهاية>>» must never be mistaken for it
    @staticmethod
    def _list_file(o):
        """True when the file block being written is a plain list (.txt / .md): only there the first item is taken from «قائمة ...: items»."""
        i = o.rfind("\x01ملف:"); j = o.find(">>", i)
        return i >= 0 and j > i and o[i + 5:j].strip().lower().endswith((".txt", ".md"))
    def _copy_dist(self, src, out, st):
        """Pointer copy (as in pointer-generator networks), INSIDE a file block only. A copy RUN starts when the last 3+ characters written also occur in
        the request, or right after an opening bracket / the first «: » of the request, and then follows the request letter by letter; it stops at a
        space (except after a comma) and at the end of the list. It copies the user's own names, items and numbers; nothing is looked up or recalled.
        st is the run state {"p": next index in src or None}. Returns (char, strength) or None."""
        if out.rfind("<<ملف:") <= out.rfind("<<نهاية>>"): st["p"] = None; return None
        o = out.replace("¶", "\n").replace("<<ملف:", "\x01ملف:"); p = st["p"]            # inside a reply a line end is written as ¶
        if p is not None and (p >= len(src) or p == 0 or o[-1:] != src[p - 1]): p = None          # the model went its own way: the run ends
        if p is None:
            if o.endswith("\x01ملف:"): p = src.find("\x01ملف:") + len("\x01ملف:") if "\x01ملف:" in src else None       # the name the user asked for
            elif o.endswith("= [") and "[" in src: p = src.find("[") + 1                   # a list literal being assigned: copy the user's list
            elif o.endswith(">>\n") and ": " in src and self._list_file(o): p = src.index(": ") + 2                    # the first item after «قائمة ...: »
            else:
                for L in range(min(12, len(o)), 2, -1):
                    pos = src.find(o[-L:])
                    if pos >= 0: p = pos + L; break
        if p is None or p >= len(src): st["p"] = None; return None
        ch = src[p]
        if ch == "\x01" or (ch == " " and o[-1:] != ","): st["p"] = None; return None
        st["p"] = p + 1
        return ch, 1.0
    def reply(self, user_text, max_chars=700, temp=0.7, topk=8, min_p=0.15, mem_gain=0.6, short_gain=0.6, learn=True, copy_gain=0.9):
        lm = self.lm; u = user_text.replace("\n", " ¶ ").strip(); nq = self._norm(u)
        self._feed("س:" + u + NL + "ج:")
        same_ask = any(q == nq for q, _ in self.replies)                         # asked the same thing again: the same answer is fine
        prev = set()
        if not same_ask:
            for _, r in self.replies[-6:]: prev |= self._grams(r, self.NG_PREV)
        out = ""; track = []; nl = lm.cid(NL, False); self_g = set(); src = self.copy_source(u); cst = {"p": None}
        for _ in range(max_chars):
            p = self._mix(self.p, mem_gain, short_gain)
            p[0] = 0; p[lm.nv:] = 0
            cd = self._copy_dist(src, out, cst) if copy_gain > 0 else None
            if cd:
                ci = lm.cid("¶" if cd[0] == "\n" else cd[0], False); lam = copy_gain * cd[1]; q = np.zeros_like(p); q[ci] = 1.0; p = (1 - lam) * p + lam * q
            if len(out) < 3 or out.rfind("<<ملف:") > out.rfind("<<نهاية>>"): p[nl] = 0           # a reply cannot end inside an open file block: the block must be closed first
            if p.sum() <= 0: p[nl] = 1.0                                           # it always writes something: a reply cannot end before it began
            # no-repeat: forbid characters that would complete a piece already written (this reply, or an earlier reply of this chat)
            file_mode = "<<ملف:" in out
            if not file_mode and (len(out) >= self.NG_PREV - 1 or len(out) >= self.NG_SELF - 1):
                for i in np.nonzero(p)[0]:
                    c = lm.chars[i]
                    if c == NL: continue
                    if (len(out) >= self.NG_SELF - 1 and (out + c)[-self.NG_SELF:] in self_g) or (len(out) >= self.NG_PREV - 1 and (out + c)[-self.NG_PREV:] in prev):
                        p[i] = 0
                if p.sum() <= 0: p[nl] = 1.0                                     # every continuation repeats: finish the reply here
            p[p < min_p * p.max()] = 0; p = p ** (1.0 / temp)
            if topk and topk < lm.nv:
                cut = np.partition(p, -topk)[-topk]; p[p < cut] = 0
            p /= p.sum(); i = int(self.rng.choice(len(p), p=p)); ch = lm.chars[i]
            track.append(float(self.p[i]))
            self.p, self.state = lm.step_char(i, self.state); self.text += ch
            if ch == NL: break
            out += ch
            if len(out) >= self.NG_SELF: self_g.add(out[-self.NG_SELF:])
            if not file_mode and len(out) >= 48 and out[-24:] in out[:-24]:                        # stuck in a loop: cut the loop off and stop
                out = out[:len(out) - 24]; break
        out = out.replace("¶", "\n")
        out = (out if "<<ملف:" in out else self.dedupe(out)).strip()          # dedupe would delete the second «<<نهاية>>» (and any repeated code line) of a file reply
        self.replies.append((nq, out)); del self.replies[:-12]
        if learn:
            self.short.add("س:" + u); lm.observe(user_text)                       # memory only (n-grams): the weights are changed by develop(), never here
        return out, track
