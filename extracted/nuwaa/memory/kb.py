# -*- coding: utf-8 -*-
"""Arabic-aware retrieval over data/kb/kb.jsonl (+ plain user/bot pairs). The Kotlin app (Kb.kt) implements the SAME algorithm:
normalize -> light stemming -> stop-words -> IDF-weighted cosine of token sets, best question phrasing per entry."""
import json, math, re
from pathlib import Path

HIGH, LOW = 0.50, 0.30          # answer directly above HIGH; "closest I have" above LOW; otherwise admit ignorance
_TASH = re.compile("[\u064b-\u0652\u0670\u0640]")
_DIG = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_TOK = re.compile("[a-z0-9_#+]+|[\u0600-\u06ff]+")
def norm(s):
    s = _TASH.sub("", s.lower()).translate(_DIG)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")): s = s.replace(a, b)
    return s

def stem(w):
    for p in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if w.startswith(p) and len(w) - len(p) >= 3: return w[len(p):]
    if len(w) > 4 and w[0] in "وبف" and w[1:3] != "ال": return w   # keep: too risky to strip single letters
    return w

_SYN_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "kb" / "syn.json"
def _load_syn():
    d = json.loads(_SYN_FILE.read_text(encoding="utf-8"))
    return ({_key(k): _key(v) for k, v in d["phrases"].items()}, {_key(k): _key(v) for k, v in d["words"].items()},
            {_key(x) for x in d["stop"]}, {_key(x) for x in d["langs"]})
def _key(x): return norm(x).strip()
def _strip_a(w):
    # first-person verb prefix: "احذف" -> "حذف". Both the KB and the query are treated the same, so this only adds recall.
    return w[1:] if len(w) >= 4 and w[0] == "ا" and w[1] != "ل" else w
PHRASES, WORDS, STOP, LANGS = _load_syn()

MEANING = {"معني", "تعني", "يعني", "مرادف", "مرادفات", "ضد", "عكس", "اضداد", "متضاد"}   # normalised: the word dictionary is consulted ONLY for these
def is_meaning(q): return bool(MEANING & set(_TOK.findall(norm(q))))

def tokens(s):
    t = norm(s)
    for a, b in PHRASES.items(): t = t.replace(a, " " + b + " ")
    out = []
    for w in _TOK.findall(t):
        w = stem(w)
        if len(w) > 3 and w[0] in "بولف" and w not in WORDS and w[1:] in WORDS: w = w[1:]    # "بجافاسكربت" -> "جافاسكربت"
        w = WORDS.get(w, w)
        if w in WORDS and WORDS[w] == "": continue
        w = _strip_a(w); w = WORDS.get(w, w)
        if w and w not in STOP: out.append(w)
    return set(out)

class KB:
    def __init__(self):
        self.items = []     # dict(id, a, v, phr=[token sets])
        self.idf = {}; self.max_idf = 1.0
    def add(self, qs, a, id="", v=-1):
        if isinstance(qs, str): qs = [qs]
        self._append(id, a, v, qs); self._reidf()
    def _append(self, id, a, v, qs):
        phr = [tokens(q) for q in qs]
        self.items.append(dict(id=id, a=a, v=v, qs=qs, phr=phr, lang=set().union(*phr) & LANGS if phr else set()))
    def _reidf(self):
        df = {}; n = 0
        for it in self.items:
            for p in it["phr"]:
                n += 1
                for t in p: df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + n / (1 + c)) for t, c in df.items()}
        self.max_idf = math.log(1 + n) if n else 1.0
    def load_jsonl(self, path):
        items = []
        for l in Path(path).read_text(encoding="utf-8").splitlines():
            if not l.strip(): continue
            d = json.loads(l)
            if "q" in d: items.append((d["q"], d["a"], d.get("id", ""), d.get("v", -1)))
            else: items.append(([d["user"]], d["bot"], "", -1))
        for qs, a, i, v in items: self._append(i, a, v, qs)
        self._reidf(); return self
    def _w(self, ts):
        top = self.max_idf
        return sum(self.idf.get(t, top) for t in ts)      # words the KB has never seen count against the match
    def search(self, q, k=3):
        qt = tokens(q)
        if not qt: return []
        wq = self._w(qt); res = []; ql = qt & LANGS
        for it in self.items:
            best = 0.0
            for p in it["phr"]:
                if not p: continue
                inter = qt & p
                if not inter: continue
                wi = self._w(inter); pq, pp = wi / wq, wi / self._w(p)
                s = 2 * pq * pp / (pq + pp)                 # harmonic mean: both sides must be covered
                if s > best: best = s
            if best > 0 and ql and it["lang"] and not (ql & it["lang"]): best *= 0.5   # asked about another language
            if best > 0: res.append((best, it))
        res.sort(key=lambda x: -x[0]); return res[:k]
    def best(self, q):
        r = self.search(q, 1); return (r[0][1], r[0][0]) if r else (None, 0.0)
