# -*- coding: utf-8 -*-
"""Build data/kb/kb.jsonl from tools/kb_entries.py. Every code sample that can be checked here IS checked; a failure stops the build.
python tools/gen_knowledge.py"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kb_entries import ENTRIES

ROOT = Path(__file__).resolve().parent.parent
LEVEL = {"py": 2, "js": 2, "sql": 1, "pyc": 0, "jsc": 0, "sh": 0, None: -1}

def run(cmd, cwd, timeout=20):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding="utf-8")

def check(e, tmp):
    c, code, exp = e["check"], e["code"], e["exp"]
    if c is None: return None
    if c == "py":
        (tmp / "m.py").write_text(code, encoding="utf-8"); r = run([sys.executable, "m.py"], tmp)
        if r.returncode: return "python failed: " + r.stderr[-300:]
        return None if r.stdout.strip() == exp else f"output {r.stdout.strip()!r} != {exp!r}"
    if c == "pyc":
        try: compile(code, "x", "exec")
        except SyntaxError as ex: return f"syntax: {ex}"
        return None
    if c in ("js", "jsc"):
        (tmp / "m.js").write_text(code, encoding="utf-8")
        r = run(["node"] + (["--check"] if c == "jsc" else []) + ["m.js"], tmp)
        if r.returncode: return "node failed: " + r.stderr[-300:]
        return None if c == "jsc" or r.stdout.strip() == exp else f"output {r.stdout.strip()!r} != {exp!r}"
    if c == "sql":
        try: sqlite3.connect(":memory:").executescript(code)
        except Exception as ex: return f"sql: {ex}"
        return None
    if c == "sh":
        (tmp / "m.sh").write_text(code, encoding="utf-8"); r = run(["bash", "-n", "m.sh"], tmp)
        return None if r.returncode == 0 else "bash syntax: " + r.stderr[-200:]
    return f"unknown check {c}"

def build(out=None):
    rows, bad = [], []
    for e in ENTRIES:
        tmp = Path(tempfile.mkdtemp())
        try: err = check(e, tmp)
        finally: shutil.rmtree(tmp, ignore_errors=True)
        if err: bad.append((e["id"], err)); continue
        a = e["text"] + (f"\n\n```{e['lang']}\n{e['code']}\n```" if e["code"] else "")
        rows.append({"id": e["id"], "q": e["qs"], "a": a, "v": LEVEL[e["check"]]})
    if bad: raise SystemExit("KNOWLEDGE CHECK FAILED:\n" + "\n".join(f"  {i}: {m}" for i, m in bad))
    default = out is None
    out = Path(out or ROOT / "data" / "kb" / "kb.jsonl"); out.parent.mkdir(parents=True, exist_ok=True)
    lex = [r for r in rows if r["id"].startswith("ar_w")]          # word meanings live in their own file (see Brain.answer / Chat.reply)
    main = [r for r in rows if not r["id"].startswith("ar_w")]
    dump = lambda rs: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs)
    out.write_text(dump(main), encoding="utf-8"); out.with_name("lexicon.jsonl").write_text(dump(lex), encoding="utf-8")
    if default:   # the same meanings as training pairs; train_only/ is read by train.py but never copied into the app's search data
        t = ROOT / "data" / "train_only"; t.mkdir(parents=True, exist_ok=True)
        (t / "lexicon_chat.jsonl").write_text("".join(json.dumps({"user": q, "bot": r["a"]}, ensure_ascii=False) + "\n" for r in lex for q in r["q"][:3]), encoding="utf-8")
    return rows

if __name__ == "__main__":
    rows = build()
    from collections import Counter
    print(len(rows), "entries OK (word meanings:", sum(r["id"].startswith("ar_w") for r in rows), "in lexicon.jsonl);", dict(Counter(r["v"] for r in rows)), "(2=ran+output matched, 1=ran, 0=syntax only, -1=not checkable here)")
