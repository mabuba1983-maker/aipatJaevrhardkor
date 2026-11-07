# -*- coding: utf-8 -*-
"""Learned vocabulary: the mind BUILDS its words from text (BPE-style merges over characters). No ready-made word list.
Words seen often enough become 'known words'; rare/new words are reported as unknown so the develop cycle can learn them."""
import json, re
from collections import Counter
from pathlib import Path

_TASHKEEL = re.compile("[\u064B-\u0652\u0640]")
_WORD = re.compile(r"\w+|[^\w\s]", re.UNICODE)

def normalize(t):
    t = _TASHKEEL.sub("", t.lower())
    return t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")

def words(t): return _WORD.findall(normalize(t))

class LearnedVocab:
    MAX_WORDS = 60000                                  # keeps the file small (budget)
    def __init__(self):
        self.merges = []; self.wf = Counter(); self._rank = {}
    def observe(self, text):
        for w in words(text): self.wf[w] += 1
    def learn_merges(self, n=400, min_pair=2):
        """Add up to n new merges on top of the existing ones (deterministic: ties broken alphabetically)."""
        if len(self.wf) > self.MAX_WORDS: self.wf = Counter(dict(self.wf.most_common(self.MAX_WORDS)))
        seqs = {w: self._apply(tuple(w)) for w in self.wf}; added = 0
        for _ in range(n):
            pairs = Counter()
            for w, s in seqs.items():
                for a, b in zip(s, s[1:]): pairs[(a, b)] += self.wf[w]
            if not pairs: break
            (a, b), c = min(pairs.items(), key=lambda kv: (-kv[1], kv[0]))
            if c < min_pair: break
            self.merges.append((a, b)); added += 1
            seqs = {w: self._merge(s, a, b) for w, s in seqs.items()}
        self._rank = {m: i for i, m in enumerate(self.merges)}; return added
    @staticmethod
    def _merge(s, a, b):
        out, i = [], 0
        while i < len(s):
            if i + 1 < len(s) and s[i] == a and s[i + 1] == b: out.append(a + b); i += 2
            else: out.append(s[i]); i += 1
        return tuple(out)
    def _apply(self, s):
        for a, b in self.merges: s = self._merge(s, a, b)
        return s
    def encode_word(self, w):
        s = tuple(w)
        while len(s) > 1:
            r = min(((self._rank.get(p, 1 << 30), p) for p in zip(s, s[1:])), default=None)
            if r is None or r[0] == 1 << 30: break
            s = self._merge(s, *r[1])
        return list(s)
    def encode(self, text): return [t for w in words(text) for t in self.encode_word(w)]
    def known(self, w, min_count=2): return self.wf.get(w, 0) >= min_count
    def unknown_words(self, text, min_count=2):
        return [w for w in words(text) if w.isalnum() and not self.known(w, min_count)]
    def coverage(self, text, min_count=2):
        ws = [w for w in words(text) if w.isalnum()]
        return 1.0 if not ws else sum(self.known(w, min_count) for w in ws) / len(ws)
    def stats(self): return {"merges": len(self.merges), "words": len(self.wf), "known_words": sum(1 for c in self.wf.values() if c >= 2)}
    def save(self, path):
        Path(path).write_text(json.dumps({"merges": self.merges, "wf": dict(self.wf.most_common(self.MAX_WORDS))}, ensure_ascii=False), encoding="utf-8")
    @classmethod
    def load(cls, path):
        v = cls(); p = Path(path)
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8")); v.merges = [tuple(m) for m in d["merges"]]; v.wf = Counter(d["wf"])
            v._rank = {m: i for i, m in enumerate(v.merges)}
        return v
