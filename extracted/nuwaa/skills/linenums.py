# -*- coding: utf-8 -*-
"""Removes line numbers that were copied together with code ("1  def f():", "12: x = 1", "  3<TAB>y = 2", "4 | z").
Mirrored in Kotlin (LineNumbers.kt). Shared cases: data/linenums_cases.json.
It only strips when the text REALLY looks numbered: >= 2 code lines carry a number, >= 80% of the non-empty lines carry one,
the numbers strictly increase and (about) follow each other. Otherwise the text is returned untouched, so normal code such as
"1 + 2" is never damaged. Returns (new_text, number_of_lines_changed)."""
import re
_D = "0-9\u0660-\u0669"
_AR = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669", "0123456789")
_BLANK = re.compile(rf"[ \t]*([{_D}]{{1,6}})[ \t\r]*")
_PRE = re.compile(rf"[ \t]*([{_D}]{{1,6}})(?:(\t)|[ \t]*([:|.)\]])[ ]?|( ))")
_NOT_CODE_START = "+*/=%<>,)"

def strip_line_numbers(text):
    lines = text.split("\n")
    rows = []; nonempty = 0; code_lines = 0
    for ln in lines:
        if not ln.strip():
            rows.append(None); continue
        nonempty += 1
        b = _BLANK.fullmatch(ln)
        if b:
            rows.append(("b", int(b.group(1).translate(_AR)), 0, "")); continue
        m = _PRE.match(ln)
        if m:
            rest = ln[m.end():].lstrip()
            style = "tab" if m.group(2) else ("punct" if m.group(3) else "space")
            bad = rest[:1] in tuple(_NOT_CODE_START) or (rest[:1] == "-" and style == "space")
            if rest and not bad:
                rows.append(("p", int(m.group(1).translate(_AR)), m.end(), style)); code_lines += 1; continue
        rows.append(("x", 0, 0, ""))
    marked = [r for r in rows if r and r[0] in "bp"]
    if code_lines < 2 or len(marked) < 0.8 * nonempty:
        return text, 0
    nums = [r[1] for r in marked]
    if any(b <= a for a, b in zip(nums, nums[1:])):
        return text, 0
    steps = len(nums) - 1
    if steps and sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1) < 0.5 * steps:
        return text, 0
    out = []; changed = 0
    for ln, r in zip(lines, rows):
        if r is None or r[0] == "x": out.append(ln)
        elif r[0] == "b": out.append(""); changed += 1
        else: out.append(ln[r[2]:]); changed += 1
    if all(r[3] == "space" for r in rows if r and r[0] == "p"):
        ind = [len(o) - len(o.lstrip(" ")) for o, r in zip(out, rows) if r and r[0] == "p" and o.strip()]
        k = min(ind) if ind else 0
        if k > 0: out = [o[k:] if (r and r[0] == "p" and o.strip()) else o for o, r in zip(out, rows)]
    return "\n".join(out), changed
