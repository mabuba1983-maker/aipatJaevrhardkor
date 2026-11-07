# -*- coding: utf-8 -*-
"""Builds a training file that is ONLY programming + Arabic.
Reads: folders / files (.py .js .ts .java .kt .c .cpp .h .cs .go .rs .sql .sh .html .css .md .txt), documents separated by a form feed (\\f), and .jsonl
instruction pairs ({"user","bot"} or {"instruction","output"}). Keeps only characters the model knows (ASCII for code + the Arabic letters and marks),
drops documents that are mostly something else (Chinese comments, emoji walls), splits into chunks of at most 600 characters (code at blank lines / defs,
Arabic at sentence ends), removes duplicates. Output: one text per line (line ends inside code are written as ¶; a pair is  س:<question>\\tج:<answer>).
  python tools/prepare_corpus.py --src raw/ my_code/ --out extra.txt --max-lines 400000
Then:  python tools/train_gru_torch.py --init ... --text extra.txt"""
import argparse, hashlib, json, os, random, re, sys

ALLOWED = set(chr(c) for c in range(32, 127)) | set(chr(c) for c in range(0x621, 0x653)) | set("٠١٢٣٤٥٦٧٨٩ـ،؛؟«»×÷•·←→“”‘’…—–\n")
CODE_EXT = {".py", ".js", ".ts", ".java", ".kt", ".c", ".cpp", ".h", ".cs", ".go", ".rs", ".sql", ".sh", ".html", ".css"}
TEXT_EXT = {".md", ".txt"}
MAXC = 600

def clean(text):
    """Returns the text restricted to the model's characters, or None if too much of it is something else."""
    text = text.replace("\r", "").replace("\t", "    ")
    n = len(text)
    if n < 40: return None
    bad = sum(1 for c in text if c not in ALLOWED)
    if bad > 0.15 * n: return None
    text = "".join(c for c in text if c in ALLOWED)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def is_code(text):
    ar = sum(1 for c in text if 0x621 <= ord(c) <= 0x652)
    return ar < 0.3 * max(1, len(text))

def chunks(text):
    """Pieces of at most MAXC characters, cut at natural places."""
    out = []; cur = ""
    parts = re.split(r"\n\n+|(?<=[.!?؟])\s+", text) if not is_code(text) else re.split(r"\n\n+|\n(?=def |class |function |public |private |import |#include)", text)
    for p in parts:
        p = p.strip("\n")
        if not p: continue
        while len(p) > MAXC:                       # one huge paragraph or function: cut at a line end if possible
            cut = p.rfind("\n", 0, MAXC); cut = cut if cut > MAXC // 3 else MAXC
            if cur: out.append(cur); cur = ""
            out.append(p[:cut]); p = p[cut:].strip("\n")
        if len(cur) + len(p) + 2 <= MAXC: cur = (cur + "\n\n" + p) if cur else p
        else:
            if cur: out.append(cur)
            cur = p
    if cur: out.append(cur)
    return [c for c in out if len(c) >= 30]

def line(c): return c.replace("\n", "¶")

def docs_from(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".jsonl":
        for l in open(path, encoding="utf-8", errors="ignore"):
            try: o = json.loads(l)
            except Exception: continue
            u = o.get("user") or o.get("instruction") or o.get("question"); b = o.get("bot") or o.get("output") or o.get("answer")
            if u and b:
                if o.get("input"): u = u + "\n" + o["input"]
                yield ("pair", u, b)
    elif ext in CODE_EXT | TEXT_EXT:
        raw = open(path, encoding="utf-8", errors="ignore").read()
        for d in raw.split("\f"): yield ("doc", d)

def walk(srcs):
    for s in srcs:
        if os.path.isdir(s):
            for r, _, fs in os.walk(s):
                for f in sorted(fs): yield os.path.join(r, f)
        elif os.path.isfile(s): yield s

def process(docs, out, max_lines=0, seed=1):
    """docs: iterable of ("doc", text) or ("pair", user, bot). Writes `out`; returns statistics."""
    seen = set(); lines = []; stats = {"docs": 0, "dropped_foreign": 0, "pairs": 0, "dupes": 0}
    for d in docs:
        if d[0] == "pair":
            u, b = clean(d[1] + " " * 40), clean(d[2] + " " * 40)
            if not u or not b or len(u) > 500 or len(b) > 1100: stats["dropped_foreign"] += 1; continue
            t = "س:" + line(u) + "\tج:" + line(b); h = hashlib.md5(t.encode()).hexdigest()
            if h in seen: stats["dupes"] += 1; continue
            seen.add(h); lines.append(t); stats["pairs"] += 1
        else:
            stats["docs"] += 1; c = clean(d[1])
            if c is None: stats["dropped_foreign"] += 1; continue
            for ch in chunks(c):
                h = hashlib.md5(ch.encode()).hexdigest()
                if h in seen: stats["dupes"] += 1; continue
                seen.add(h); lines.append(line(ch))
    random.Random(seed).shuffle(lines)
    if max_lines: lines = lines[:max_lines]
    with open(out, "w", encoding="utf-8") as f:
        for l in lines: f.write(l + "\n")
    chars = sum(len(l) for l in lines); ar = sum(1 for l in lines for c in l if 0x621 <= ord(c) <= 0x652)
    stats.update(lines=len(lines), characters=chars, arabic_percent=round(100 * ar / max(1, chars)))
    return stats

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--src", nargs="+", required=True); ap.add_argument("--out", required=True); ap.add_argument("--max-lines", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1); a = ap.parse_args(argv)
    def gen():
        for path in walk(a.src):
            yield from docs_from(path)
    st = process(gen(), a.out, a.max_lines, a.seed)
    print(f"{a.out}: {st['lines']:,} lines, {st['characters'] / 1e6:.1f} M characters ({st['arabic_percent']}% Arabic letters)", st)

if __name__ == "__main__": main()
