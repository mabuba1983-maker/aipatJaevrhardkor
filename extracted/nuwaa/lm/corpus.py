# -*- coding: utf-8 -*-
"""Base text for pretraining: only the project's own Arabic dialogue data. One turn pair per line:  س:<user>\\nج:<bot>\\n  (line breaks inside a reply become ¶)."""
import json, re
from pathlib import Path
ARABIC = re.compile(r"[\u0621-\u064A]")

def pairs(data="data"):
    d = Path(data); out = []
    for f in ("arabic_chat.jsonl", "instructions_ar.jsonl", "train_only/lexicon_chat.jsonl", "python_chat.jsonl"):
        p = d / f
        if not p.exists(): continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            j = json.loads(line); u, b = j.get("user", ""), j.get("bot", "")
            if "```" in b or len(ARABIC.findall(u + b)) < 0.5 * len(u + b) * 0.6: continue
            out.append((u.strip(), b.strip()))
    return out

def fmt(u, b): return "س:" + u.replace("\n", " ¶ ") + "\nج:" + b.replace("\n", "¶") + "\n"
def base_text(data="data"): return "".join(fmt(u, b) for u, b in pairs(data))
def clean(s): return s.replace("¶", "\n").strip()


# ---------------- corpus for the recurrent model (GRULM): everything is TRAINING TEXT now, nothing is looked up as a canned answer ----------------
_OLD = ("تعلم:", "زر التطوير", "بصراحة إني ما أعرف", "المدقق", "لا أعدل نفسي", "اختبار التحقق", "أحفظ فقط اللي")     # old lines that describe the retired canned behaviour

def _jsonl(p):
    out = []
    if not p.exists(): return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except ValueError: pass
    return out

def all_pairs(data="data", max_bot=1200):
    """All (user, bot) pairs: dialogue files, the python basics, self-development talk, word meanings and the verified knowledge base (code included)."""
    d = Path(data); out = []
    for f in ("arabic_chat.jsonl", "instructions_ar.jsonl", "python_chat.jsonl", "python_basics_ar.jsonl", "self_dev_ar.jsonl", "generated_python.jsonl", "v16_arabic.jsonl", "v16_code.jsonl", "v16_fix.jsonl", "v16_tasks.jsonl", "v17_files.jsonl", "v17_chat.jsonl", "v18_seed.jsonl", "v19_seed2.jsonl", "v20_think.jsonl", "v21_english.jsonl", "v22_arabic_full.jsonl", "v23_advanced.jsonl", "train_only/lexicon_chat.jsonl", "user_feedback.jsonl"):
        for j in _jsonl(d / f):
            u, b = j.get("user", "").strip(), j.get("bot", "").strip()
            if u and b and len(b) <= max_bot and not any(w in b for w in _OLD): out.append((u, b))
    for j in _jsonl(d / "kb" / "kb.jsonl"):
        a = j.get("a", "").strip()
        if a and len(a) <= max_bot:
            for q in j.get("q", [])[:2]: out.append((q.strip(), a))
    return out
