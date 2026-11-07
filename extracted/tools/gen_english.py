# -*- coding: utf-8 -*-
"""English + Arabic + Python pairs from tools/seed_data4.py. Every python example is RUN and its real output is written in the answer. -> data/v21_english.jsonl"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed as g
from gen_fix import run_out
from seed_data4 import TERMS, GRAMMAR, PHRASES, ENQA
R = random.Random(21); F = "```"

def out_line(code):
    rc, so = run_out(code)
    return None if rc != 0 else so.strip().replace("\n", " ، ")

def main():
    pairs = []; dropped = []
    for term, ar, en, code in TERMS:
        o = out_line(code)
        if o is None: dropped.append(term); continue
        ex = "\nمثال:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + o
        pairs.append((f"ماذا تعني كلمة {term} في البرمجة؟", f"{term}: {ar}. بالإنجليزية: {en}." + ex))
        pairs.append((f"ما ترجمة {term} في بايثون؟", f"{term} تعني: {ar}." ))
        pairs.append((f"What does {term} mean in Python?", f"In Python, {term} means {en}.\nبالعربي: {ar}.\n" + F + "python\n" + code + "\n" + F + "\nOutput: " + o))
    for topic, ar, ex in GRAMMAR:
        pairs.append((f"اشرح {topic}", ar + "\nأمثلة:\n" + "\n".join(ex)))
        pairs.append((f"Give me examples of {topic.split(' ', 1)[-1]}", "\n".join(ex)))
    for a, e in PHRASES:
        pairs.append((f"ترجم للإنجليزية: {a}", e)); pairs.append((f"ترجم للعربية: {e}", a)); pairs.append((f"Translate to Arabic: {e}", a)); pairs.append((f"Translate to English: {a}", e))
    for q, a, code in ENQA:
        if code:
            o = out_line(code)
            if o is None: dropped.append(q); continue
            a = a + "\n" + F + "python\n" + code + "\n" + F + "\nOutput: " + o
        pairs.append((q, a)); pairs.append((q.lower().rstrip("?") + "?", a))
    pairs = [(u, b) for u, b in dict.fromkeys(pairs) if u not in g.EVAL and len(b) <= 1150]
    with open("data/v21_english.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "dropped", dropped)

if __name__ == "__main__": main()
