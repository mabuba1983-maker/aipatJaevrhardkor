"""Untrusted text from the phone -> safe training pairs. Drops anything malformed, oversized or with control characters."""
import json, os, re, sys
from pathlib import Path
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def sanitize_lines(text, max_len=2000, max_lines=2000):
    out, seen = [], set()
    for line in text.splitlines()[-max_lines:]:
        try: d = json.loads(line)
        except Exception: continue
        if not isinstance(d, dict): continue
        u, b = d.get("user"), d.get("bot")
        if not (isinstance(u, str) and isinstance(b, str)): continue
        u, b = u.strip(), b.strip()
        if not u or not b or len(u) > max_len or len(b) > max_len or _CTRL.search(u + b) or (u, b) in seen: continue
        seen.add((u, b)); out.append(json.dumps({"user": u, "bot": b}, ensure_ascii=False))
    return out

def ingest(text, dst="data/user_feedback.jsonl"):
    lines = sanitize_lines(text)
    if lines:
        Path(dst).parent.mkdir(exist_ok=True)
        with open(dst, "a", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    return len(lines)

if __name__ == "__main__": print("ingested", ingest(os.environ.get("LEARNED", "")))
