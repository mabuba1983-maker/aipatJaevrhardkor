# -*- coding: utf-8 -*-
"""The developer file («ملف المطور»): what the model hands out after developing itself, and the checker that says whether it is broken.
A developer file is a ZIP with:  manifest.json (report + sha256 of the other files) · nlm2.bin (the weights, format NLM2) · memory.txt (long-term memory: one line per thing heard).
  python -m nuwaa.lm.devfile check  FILE.zip [--base assets/nlm2.bin] [--data data]     -> verdict OK / BROKEN with the reasons
Honest limit: the file carries new WEIGHTS and MEMORY. It never carries code, and nothing in it is executed."""
import hashlib, io, json, sys, time, zipfile
import numpy as np
from .gru import GRULM, Session

VERSION = 1
MAX_BYTES = 40_000_000

def _sha(b): return hashlib.sha256(b).hexdigest()

def make(lm, memory_lines, report=None):
    """Returns the bytes of a developer file."""
    w = lm.to_bytes(); mem = "\n".join(memory_lines).encode("utf-8")
    man = dict(version=VERSION, created=int(time.time()), params=lm.n_params(), vocab=lm.nv, emb=lm.E, hid=lm.H, memory_lines=len(memory_lines),
               files={"nlm2.bin": _sha(w), "memory.txt": _sha(mem)}, report=report or {})
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(man, ensure_ascii=False, indent=1)); z.writestr("nlm2.bin", w); z.writestr("memory.txt", mem)
    return bio.getvalue()

PROMPTS = ["مرحبا", "ما هي بايثون", "كيف اطبع نص في بايثون", "كيف تتعلم", "اكتب دالة تجمع رقمين", "ما هو ملف المطور"]

def check(path, base=None, data="data", say=print):
    """Returns (ok, reasons[list], facts[dict]). Every check says what it found; a single failed check means BROKEN."""
    bad = []; facts = {}
    def fail(m): bad.append(m); say("✗ " + m)
    def good(m): say("✓ " + m)
    try:
        with open(path, "rb") as fh: raw = fh.read()
        if len(raw) > MAX_BYTES: return False, ["الملف أكبر من الحد"], facts
        z = zipfile.ZipFile(io.BytesIO(raw)); assert z.testzip() is None
    except Exception as e: return False, [f"الملف مو zip سليم: {type(e).__name__}"], facts
    names = set(z.namelist())
    for n in ("manifest.json", "nlm2.bin", "memory.txt"):
        if n not in names: fail(f"ناقص: {n}")
    if bad: return False, bad, facts
    try: man = json.loads(z.read("manifest.json").decode("utf-8"))
    except Exception: return False, ["manifest.json غير صالح"], facts
    for n, h in man.get("files", {}).items():
        if n in names and _sha(z.read(n)) != h: fail(f"{n}: البصمة ما تطابق (الملف تغيّر أو انكسر)")
    if not bad: good("الملف سليم والبصمات تطابق")
    try: mem = z.read("memory.txt").decode("utf-8"); good(f"الذاكرة طويلة المدى: {len(mem.splitlines())} سطر، UTF-8 سليم")
    except Exception: fail("memory.txt ليس UTF-8"); mem = ""
    try:
        lm = GRULM.from_bytes(z.read("nlm2.bin")); facts["params"] = lm.n_params()
        for k, v in lm.P.items():
            if not np.isfinite(v).all(): fail(f"الأوزان فيها NaN أو لا نهاية في {k}")
        if not bad: good(f"الأوزان تُقرأ وكلها أرقام سليمة ({lm.n_params()} معامل، {lm.nv} حرف)")
    except Exception as e: fail(f"تعذر قراءة الأوزان: {type(e).__name__}: {e}"); return False, bad, facts
    if bad: return False, bad, facts
    from .corpus import all_pairs, fmt
    pairs = all_pairs(data); text = "".join(fmt(*p) for p in pairs[::7]); ids = lm.encode(text, grow=False); b = lm.bpc(ids); facts["bits_per_char"] = round(b, 3)
    ref = None
    if base:
        bm = GRULM.from_bytes(open(base, "rb").read()); ref = bm.bpc(bm.encode(text, grow=False)); facts["base_bits_per_char"] = round(ref, 3)
    if ref is not None and b > ref + 0.6: fail(f"صار أسوأ من الأساس: {b:.2f} بت/حرف مقابل {ref:.2f}")
    elif ref is None and b > 5.5: fail(f"النموذج ما يتنبأ بالنص أصلا ({b:.2f} بت/حرف)")
    else: good(f"جودته على بيانات المشروع: {b:.2f} بت/حرف" + (f" (الأساس {ref:.2f})" if ref is not None else ""))
    s = Session(lm, seed=1); empty = 0
    for q in PROMPTS:
        try:
            r, _ = s.reply(q, max_chars=200, learn=False)
            if not r.strip(): empty += 1
        except Exception as e: fail(f"انهار وهو يكتب رد: {type(e).__name__}"); break
    if empty: fail(f"{empty} من {len(PROMPTS)} ردود طلعت فاضية")
    elif not bad: good(f"كتب {len(PROMPTS)} ردود بدون انهيار وبدون فراغ")
    return not bad, bad, facts

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "check":
        base = a[a.index("--base") + 1] if "--base" in a else None; data = a[a.index("--data") + 1] if "--data" in a else "data"
        ok, why, facts = check(a[1], base, data); print("\nالنتيجة:", "سليم ✅" if ok else "مكسور ❌", facts); sys.exit(0 if ok else 1)
    print(__doc__)
