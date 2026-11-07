"""Exact arithmetic skill (no eval). The neural net is never trusted for maths: if the whole message is a calculation, this answers it.
Mirrored in Kotlin (Skills.kt). Shared cases: data/skills_cases.json"""
import re
_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
_WORDS = [("مقسوم على", "/"), ("زائد", "+"), ("ناقص", "-"), ("ضرب", "*"), ("تقسيم", "/"), ("×", "*"), ("÷", "/"), ("^", "**")]
_FILLER = ["كم يساوي", "كم ناتج", "كم حاصل", "احسب لي", "احسب", "ناتج", "ما هو", "ما هي", "؟", "?", "=", "يساوي"]

class _P:
    def __init__(s, t): s.t, s.i = t, 0
    def peek(s): return s.t[s.i] if s.i < len(s.t) else ""
    def eat(s, c):
        if s.t.startswith(c, s.i): s.i += len(c); return True
        return False
    def expr(s):
        v = s.term()
        while True:
            if s.eat("+"): v += s.term()
            elif s.eat("-"): v -= s.term()
            else: return v
    def term(s):
        v = s.pw()
        while True:
            if s.eat("**"): raise ValueError
            if s.eat("*"): v *= s.pw()
            elif s.eat("/"):
                d = s.pw()
                if d == 0: raise ZeroDivisionError
                v /= d
            elif s.eat("%"): v %= s.pw()
            else: return v
    def pw(s):
        b = s.unary()
        if s.eat("**"):
            e = s.pw()
            if abs(e) > 100 or abs(b) > 1e6: raise OverflowError
            return b ** e
        return b
    def unary(s):
        if s.eat("-"): return -s.unary()
        if s.eat("+"): return s.unary()
        if s.eat("("):
            v = s.expr()
            if not s.eat(")"): raise ValueError
            return v
        m = re.compile(r"\d+(\.\d+)?").match(s.t, s.i)
        if not m: raise ValueError
        s.i = m.end(); return float(m.group()) if "." in m.group() else int(m.group())

def _fmt(v):
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15: return str(int(v))
        return f"{v:.6g}"
    return str(v)

def try_math(text: str):
    """Return an answer string if the message is purely a calculation, else None."""
    t = text.translate(_AR)
    for f in _FILLER: t = t.replace(f, " ")
    for w, o in _WORDS: t = t.replace(w, f" {o} ")
    t = re.sub(r"\s+", "", t)
    if not t or not re.fullmatch(r"[0-9+\-*/().%]+", t) or not re.search(r"\d.*[+\-*/%].*\d", t): return None
    p = _P(t)
    try:
        v = p.expr()
        if p.i != len(t): return None
    except ZeroDivisionError: return "لا يمكن القسمة على صفر."
    except OverflowError: return "الرقم كبير جدا."
    except (ValueError, RecursionError): return None
    shown = text.translate(_AR)
    for f in _FILLER: shown = shown.replace(f, " ")
    for w, o in _WORDS[:-1]: shown = shown.replace(w, f" {o} ")
    shown = re.sub(r"\s+", " ", shown).strip()
    return f"{shown} = {_fmt(v)}"
