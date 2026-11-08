# -*- coding: utf-8 -*-
"""Does the loaded neural engine actually understand? Ask it questions it was trained on and compare with the known answer.
Works with any object that has reply(text, max_new=...) -> str, so it is testable without PyTorch."""
import difflib, random

def engine_selftest(engine, pairs, n=8, max_new=120, sim=0.8, seed=0):
    pairs = [p for p in pairs if isinstance(p, dict) and "user" in p and "bot" in p]
    if not pairs: return dict(n=0, ok=0, rate=None, empty=0, failed=[])
    random.Random(seed).shuffle(pairs); pairs = pairs[:n]; ok = empty = 0; failed = []
    for p in pairs:
        try: out = engine.reply(p["user"], max_new=max_new)
        except Exception as e: out = ""; failed.append({"q": p["user"], "error": type(e).__name__}); continue
        if not out.strip(): empty += 1
        if difflib.SequenceMatcher(None, out.strip(), p["bot"].strip()[:max_new]).ratio() >= sim: ok += 1
        elif len(failed) < 3: failed.append({"q": p["user"], "got": out[:80]})
    return dict(n=len(pairs), ok=ok, rate=round(ok / len(pairs), 2), empty=empty, failed=failed)
