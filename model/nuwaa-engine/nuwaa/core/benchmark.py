"""Real strength tests on held-out items (data/eval/*.jsonl is never trained on). Categories: arabic, chat, code.
Item: {"category", "user", "expect": [substrings, any must appear]}  or  {"category":"code", "user", "test": "assert solve(3)==9"}"""
import glob, json, re
from ..sandbox.snippet import run_snippet

def _code(reply):
    m = re.search(r"```(?:python)?\n(.*?)```", reply, re.S)
    return (m.group(1) if m else reply).strip()

def load_items(eval_dir="data/eval"):
    items = []
    for f in sorted(glob.glob(f"{eval_dir}/*.jsonl")):
        items += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    return items

def run_benchmark(reply_fn, eval_dir="data/eval"):
    res = {}
    for it in load_items(eval_dir):
        r = reply_fn(it["user"])
        ok = run_snippet(_code(r) + "\n" + it["test"]) if "test" in it else any(e in r for e in it["expect"])
        a = res.setdefault(it["category"], [0, 0]); a[0] += int(ok); a[1] += 1
    out = {k: round(v[0] / v[1], 4) for k, v in res.items()}
    out["counts"] = {k: v[1] for k, v in res.items()}
    out["total"] = round(sum(v[0] for v in res.values()) / max(1, sum(v[1] for v in res.values())), 4)
    return out
