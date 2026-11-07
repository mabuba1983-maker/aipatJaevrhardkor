# -*- coding: utf-8 -*-
"""Question analysis, general (no word is special-cased): a message is split into
  frame words   : question words (type: place/time/quantity/reason/manner/person/thing/yesno) + function words that carry no topic
  content words : everything else = what the message is ABOUT
Both come from data/kb/interrogatives.json, so adding a dialect word is a data change, not a code change.
Tokens are folded only (letters, tashkeel, digits, punctuation, the article ال). NO synonym mapping here: the programming KB maps
e.g. «مفتاح» to its own concept «key», which is exactly the kind of old knowledge that must not steal a taught word."""
import json, re
from functools import lru_cache
from pathlib import Path
from ..memory.kb import norm

_PUNCT = re.compile(r"[\u060c\u061b\u061f\u066a-\u066d\u06d4!?.,;:()\[\]{}\"'«»<>\-_/\\|]")
_RES = Path(__file__).resolve().parent.parent.parent / "data" / "kb" / "interrogatives.json"

@lru_cache(maxsize=1)
def resource():
    j = json.loads(_RES.read_text(encoding="utf-8")); f = lambda xs: {strip_al(norm(x).strip()) for x in xs if norm(x).strip()}
    types = {}
    for t, ws in j["types"].items():
        for w in ws: types[strip_al(norm(w).replace(" ", ""))] = t
    return {"types": types, "request": f(j.get("request", [])), "function": f(j["function"]), "answer_place": f(j["answer_place"]), "answer_time": f(j["answer_time"])}

def strip_al(w):
    for p in ("وال", "بال", "كال", "فال", "لل", "ال"):
        if w.startswith(p) and len(w) - len(p) >= 2: return ("ل" if p == "لل" else "") + w[len(p):]
    return w

def words(s): return [w for w in re.sub(r"\s+", " ", _PUNCT.sub(" ", norm(s))).split(" ") if w]

def variants(w):
    """The word as typed (article removed) and, for long words, without a one-letter clitic (والقلم -> قلم, بالدرج -> درج)."""
    a = strip_al(w); out = [a]
    if len(a) > 3 and a[0] in "وبلفك": out.append(strip_al(a[1:]))
    return out

def analyze(text):
    """-> dict(tokens, qtype, content=[...], frame=[...])  tokens are canonical (article stripped)."""
    R = resource(); toks = [variants(w)[0] for w in words(text)]; qtype = None; content = []; frame = []
    for t in toks:
        if t in R["types"]:
            qtype = qtype or R["types"][t]; frame.append(t)
        elif t in R["function"]: frame.append(t)
        else: content.append(t)
    return {"tokens": toks, "qtype": qtype, "content": content, "frame": frame}

def is_request(text):
    """Does the message open with a request word (اكتب، اشرح، ابغى ...)? Then it is asking for something, not telling something."""
    w = words(text)[:1]
    return bool(w) and strip_al(w[0]) in resource()["request"]

def answer_type(ans):
    """What kind of answer is this, judged from its first word (فوق/داخل/... = place)? None when unknown."""
    R = resource(); w = words(ans)[:1]
    if not w: return None
    w = strip_al(w[0])
    return "place" if w in R["answer_place"] else "time" if w in R["answer_time"] else "quantity" if w.isdigit() else None
