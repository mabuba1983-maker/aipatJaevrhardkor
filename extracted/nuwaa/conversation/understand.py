# -*- coding: utf-8 -*-
"""Fahm (فهم): the understanding layer that sits between the user's message and the answer sources.
Pure Python, no GPU, no training, no downloads. It wraps the retrieval KB with four things the KB alone does not do:
  1. spelling repair   : "بايثوون" / "pyhton" / "الداله" are fixed against the words the KB actually knows
  2. follow-up context : "وفي جافاسكربت؟" after a Python question re-asks the SAME question for the new language
  3. ambiguity guard   : a one-word query is never answered with an unrelated entry that merely contains that word
  4. route tracing     : every reply says which source produced it, so you can see whether the message reached the engine
It never invents an answer: if nothing is close enough it returns route "none" and the caller falls through."""
import re
from collections import OrderedDict, Counter
from ..memory.kb import KB, HIGH, LOW, norm, tokens, stem, WORDS, STOP, LANGS, _TOK

_REP = re.compile(r"(.)\1{2,}")                       # "كيييف" -> "كيف"
_LATIN = re.compile(r"^[a-z0-9_#+]+$")
MORE_CUES = {norm(x) for x in ("مثال", "امثله", "اكثر", "تفصيل", "تفاصيل", "اشرح", "وضح", "كمل", "زياده", "ثاني", "اخر", "غيره", "بعده", "وبعدين")}

_PUNCT = re.compile("[\u060c\u061b\u061f\u066a-\u066d\u06d4!?.,;:()\\[\\]{}\"«»]")
def clean_query(q):
    """The KB tokenizer treats the Arabic question mark and comma as letters (they sit in the Arabic Unicode block), so
    \"سعادة؟\" never matched \"سعادة\". Punctuation becomes a space before any matching."""
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", q)).strip()

def _osa(a, b, cap):
    """Optimal-string-alignment distance (insert/delete/replace/swap-adjacent) with an early cutoff."""
    if abs(len(a) - len(b)) > cap: return cap + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b); lo = cur[0]
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]: v = min(v, prev2[j - 2] + 1)
            cur[j] = v; lo = min(lo, v)
        if lo > cap: return cap + 1
        prev2, prev = prev, cur
    return prev[-1]

class Fahm:
    def __init__(self, index: KB, max_sessions=500):
        self.index = index
        self.sessions = OrderedDict(); self.max_sessions = max_sessions
        self.stats = Counter()
        self._vocab = None

    # ---- vocabulary used for spelling repair ----
    def _build_vocab(self):
        v = Counter()
        for it in self.index.items:
            for q in it["qs"]:
                for w in _TOK.findall(norm(q)): v[w] += 1
        self._vocab = v

    def vocab(self):
        if self._vocab is None: self._build_vocab()
        return self._vocab

    def reload(self): self._vocab = None

    def _fix_word(self, w):
        v = self.vocab()
        if w in v or w in WORDS or w in STOP or w in LANGS or len(w) < 5 or w.isdigit(): return w
        if stem(w) in v or stem(w) in WORDS: return w
        cap = 1 if len(w) < 7 else 2
        best = None
        for c, n in v.items():
            if c[0] != w[0] or abs(len(c) - len(w)) > cap or len(c) < 4: continue
            d = _osa(w, c, cap)
            if d <= cap and (best is None or (d, -n) < (best[0], -best[1])): best = (d, n, c)
        return best[2] if best else w

    def repair(self, q):
        """Returns the query with unknown words replaced by their closest known word (or q unchanged)."""
        q2 = _REP.sub(r"\1", norm(q))
        words = _TOK.findall(q2); fixed = [self._fix_word(w) for w in words]
        return " ".join(fixed) if fixed != words else (q2 if q2 != norm(q) else q)

    # ---- sessions ----
    def _sess(self, sid):
        s = self.sessions.get(sid)
        if s is None: s = self.sessions[sid] = {}
        self.sessions.move_to_end(sid)
        while len(self.sessions) > self.max_sessions: self.sessions.popitem(last=False)
        return s

    # ---- retrieval ----
    def _best(self, q):
        r = self.index.search(q, 1)
        return (r[0][1], r[0][0]) if r else (None, 0.0)

    @staticmethod
    def _content(q):
        """Meaningful tokens: drops stop-words that carry a one-letter clitic (\"وفي\" = \"و\"+\"في\")."""
        return {t for t in tokens(q) if not (len(t) > 2 and t[0] in "وف" and t[1:] in STOP)}

    def _ambiguous(self, q, it, score=0.0):
        """True when the match is not trustworthy: a one-word query matched to an entry that is about more than that word,
        or a longer query that shares only a single word with the entry (e.g. only \"loop\" out of \"how do I make a loop in python\")."""
        qt, qc = tokens(q), self._content(q)
        if len(qc) <= 1: return not any(p == qt or p == qc for p in it["phr"])
        return len(qc) >= 3 and score < 0.85 and max(len(qc & p) for p in it["phr"]) <= 1

    def _swap_lang(self, last_q, q):
        """\"وفي جافاسكربت؟\" after \"كيف اطبع نص في بايثون\" -> \"كيف اطبع نص في جافاسكربت\" (None if q is not a pure language switch)."""
        qw = _TOK.findall(norm(q))
        new = [w for w in qw if WORDS.get(w, WORDS.get(stem(w), w)) in LANGS or w in LANGS]
        rest = [w for w in qw if w not in new and self._content(w)]
        if not new or rest or not last_q: return None
        lw = _TOK.findall(norm(last_q)); sw = False; out = []
        for w in lw:
            if WORDS.get(w, WORDS.get(stem(w), w)) in LANGS or w in LANGS: out.append(new[0]); sw = True
            else: out.append(w)
        return " ".join(out) if sw else None

    def understand(self, q, sid="default"):
        """-> dict(route, reply, score, id, query). route is one of: kb, kb-spell, kb-context, context-more, ambiguous, none."""
        q = clean_query(q); s = self._sess(sid); res = dict(route="none", reply=None, score=0.0, id="", query=q)
        qn = norm(q); words = _TOK.findall(qn)
        # 1) follow-up asking for a language switch
        sw = self._swap_lang(s.get("q"), q) if s.get("q") else None
        if sw:
            it, sc = self._best(sw)
            if it and sc >= HIGH and not self._ambiguous(sw, it, sc):
                res.update(route="kb-context", reply=it["a"], score=sc, id=it["id"], query=sw); return self._done(s, res, sw)
        # 2) "more / example / explain" about the previous topic
        if s.get("id") and len(words) <= 5 and any(w in MORE_CUES for w in words) and self._best(q)[1] < LOW:
            near = [it for sc, it in self.index.search(s["q"], 6) if it["id"] != s["id"] and sc >= LOW][:3]
            if near:
                lst = " أو ".join("«" + it["qs"][0] + "»" for it in near)
                res.update(route="context-more", reply="هذا اللي عندي عن الموضوع في الجواب السابق. مواضيع قريبة تقدر تسأل عنها: " + lst, score=LOW, id=s["id"]); return self._done(s, res, None)
        # 3) direct, then spelling-repaired
        it, sc = self._best(q); route = "kb"
        fixed = self.repair(q)
        if fixed != q:
            it2, sc2 = self._best(fixed)
            if it2 and sc2 > sc + 0.05: it, sc, route, res["query"] = it2, sc2, "kb-spell", fixed
        if it and sc >= HIGH:
            if self._ambiguous(res["query"], it, sc):
                res.update(route="ambiguous", score=sc); return self._done(s, res, None)
            res.update(route=route, reply=it["a"], score=sc, id=it["id"]); return self._done(s, res, res["query"])
        res["score"] = sc; return self._done(s, res, None)

    def _done(self, s, res, topic):
        if topic is not None: s["q"], s["id"] = topic, res["id"]
        self.stats[res["route"]] += 1
        return res

    def suggestions(self, q, k=2):
        q = clean_query(q); out = []
        for qq in (q, self.repair(q)):
            for sc, it in self.index.search(qq, 6):
                if sc >= LOW and it["qs"][0] not in out: out.append(it["qs"][0])
        return out[:k]
