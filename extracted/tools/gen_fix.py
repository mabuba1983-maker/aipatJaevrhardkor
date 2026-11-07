# -*- coding: utf-8 -*-
"""Idea 2: bug-fix pairs. Takes verified Python snippets, plants ONE bug (rename, dropped colon, unclosed bracket, wrong operator),
and keeps the pair only if the BROKEN code really fails and the FIXED code really runs. Output: data/v16_fix.jsonl."""
import json, os, random, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from v16_code import TASKS, F
from gen_v16 import runs, EVAL

R = random.Random(21)

def run_out(code):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py"); open(p, "w", encoding="utf-8").write(code)
        try:
            r = subprocess.run([sys.executable, p], capture_output=True, timeout=5, cwd=d, text=True)
            return r.returncode, r.stdout
        except Exception:
            return 1, ""

def plant(code):
    """Returns (broken_code, short Arabic description) or None."""
    opts = []
    lines = code.split("\n")
    for i, ln in enumerate(lines):
        if ln.rstrip().endswith(":") and ln.lstrip().startswith(("if ", "for ", "while ", "def ", "elif ", "else", "try", "except", "with ")):
            nl = lines[:]; nl[i] = ln.rstrip()[:-1]
            opts.append(("\n".join(nl), "نسيت النقطتين : في آخر السطر"))
        m = re.search(r"\(([^()]*)\)", ln)
        if m and ln.count("(") == ln.count(")"):
            nl = lines[:]; nl[i] = ln[:m.end() - 1] + ln[m.end():]
            opts.append(("\n".join(nl), "قوس مفتوح ما انسكر"))
        if "return " in ln:
            nl = lines[:]; nl[i] = ln.replace("return ", "retrun ", 1)
            opts.append(("\n".join(nl), "كلمة return مكتوبة غلط"))
    if not opts: return None
    return R.choice(opts)

def main():
    pairs = []; tried = 0; kept = 0
    for qs, c in TASKS:
        if "print" not in c or not runs(c): continue
        ok_out = run_out(c)
        for _ in range(2):
            pl = plant(c); tried += 1
            if not pl: break
            broken, what = pl
            if run_out(broken)[0] == 0: continue        # the bug must really break it
            if run_out(c)[0] != 0: continue
            q = R.choice(["هذا الكود فيه خطأ، صححه:", "ليش هذا الكود ما يشتغل؟ صححه:", "صلّح هذا الكود:"])
            user = q + "\n" + F + "python\n" + broken + "\n" + F
            bot = "الخطأ: " + what + ".\nالكود الصحيح:\n" + F + "python\n" + c + "\n" + F
            if user in EVAL or len(bot) > 1150: continue
            pairs.append((user, bot)); kept += 1
    with open("data/v16_fix.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("tried", tried, "kept", kept)

if __name__ == "__main__":
    main()
