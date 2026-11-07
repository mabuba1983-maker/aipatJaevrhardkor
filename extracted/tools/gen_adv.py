# -*- coding: utf-8 -*-
"""Advanced programming seeds -> data/v23_advanced.jsonl. Every example is RUN; its real output is written in the answer."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen_seed as g
from gen_fix import run_out
from seed_data5 import DS, PATTERNS, TESTING
R = random.Random(23); F = "```"

def main():
    pairs = []; dropped = []
    for qs, idea, steps, code in DS:
        rc, so = run_out(code)
        if rc != 0: dropped.append(qs[0]); continue
        a = "الفكرة: " + idea + "\nالخطوات:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) + "\nالكود:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
        if len(a) <= 1260:
            for q in g.variants(qs): pairs.append((q, a))
        else: dropped.append("long:" + qs[0])
    for name, desc, code in PATTERNS:
        rc, so = run_out(code)
        if rc != 0: dropped.append(name); continue
        a = desc + "\nمثال:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
        for q in [f"اشرح نمط {name} في البرمجة", f"ما هو {name} design pattern", f"اعطني مثال على {name}"]:
            if len(a) <= 1260: pairs.append((q, a))
    for qs, desc, code in TESTING:
        rc, so = run_out(code)
        if rc != 0: dropped.append(qs[0]); continue
        a = desc + "\nمثال:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + so.strip().replace("\n", " ، ")
        if len(a) <= 1260:
            for q in g.variants(qs): pairs.append((q, a))
    pairs = [(u, b) for u, b in pairs if u not in g.EVAL]
    with open("data/v23_advanced.jsonl", "w", encoding="utf-8") as f:
        for u, b in pairs: f.write(json.dumps({"user": u, "bot": b}, ensure_ascii=False) + "\n")
    print("pairs", len(pairs), "dropped", dropped)

if __name__ == "__main__": main()
