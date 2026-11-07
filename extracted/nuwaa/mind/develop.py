# -*- coding: utf-8 -*-
"""Study + self-development. Both start ONLY from a human button press (single-use, expires). They work on a COPY of `learned/`,
verify everything, and swap it in only if it is strictly better and you approved. The old version is kept (SHA-256 snapshot) and can be rolled back.

  python -m nuwaa.mind.develop press            # what the app's button does
  python -m nuwaa.mind.develop study [--approve]    # learn the basics (words + level 1-2 programming). Allowed on an empty mind.
  python -m nuwaa.mind.develop develop [--approve]  # self-development. LOCKED until the mind passes the programming exam.
  python -m nuwaa.mind.develop rollback"""
import argparse, json, os, shutil, sys, tempfile, time
from pathlib import Path
from ..selfimprove.button import record_press, consume_press
from ..versioning.store import VersionStore
from .mind import Mind
from .synth import Library, deps
from .verify import verify_skill, source_problems
from . import curriculum as cur

PRESS = "mind_press.json"

def press(root=".", source="app"): record_press(Path(root) / PRESS, source)

def _log(root, rec, say=print):
    rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(Path(root) / "mind_log.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    say(json.dumps(rec, ensure_ascii=False, indent=2)); return rec

def _eval_vocab_coverage(m, root):
    qs = []
    for f in (Path(root) / "data" / "eval").glob("*.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            try: qs.append(json.loads(l)["user"])
            except Exception: pass
    return round(sum(m.vocab.coverage(q) for q in qs) / len(qs), 4) if qs else 0.0

_VAL = []
def _lm_val_pairs():
    if not _VAL:
        from .lmdata import random_pairs
        from .lmtrain import split
        _VAL.extend(split(random_pairs(3000, seed=999))[1])             # programs the weights never train on (hash split), identical for before/after
    return _VAL

def lm_metrics(m):
    """lm_fit = 1/perplexity on never-trained programs (higher = the weights learned more). lm_solve = exam tasks the weights alone solve from the description."""
    lm = m.load_lm()
    if lm is None: return {"lm_fit": 0.0, "lm_solve": 0.0}
    from .lm import build_dataset
    ppl = lm.perplexity(*build_dataset(lm, _lm_val_pairs()))
    solved = sum(1 for t in cur.EXAM if m.lm_propose(t) is not None) / len(cur.EXAM)
    return {"lm_fit": round(1 / ppl, 4), "lm_solve": round(solved, 3)}

def metrics(m, root):
    ex = m.exam(); return {"exam": ex["score"], "exam_hard": m.exam_hard(), "skills": len(m.lib.skills), "ops": len(m.lib.ops), "coverage": _eval_vocab_coverage(m, root), **lm_metrics(m)}

def lm_step(cand, mode, say=print):
    """Teach the weights: fresh machine-made programs + every lesson/skill the mind has verified. Grows the hidden layer when learning stalls and memory allows."""
    from .lm import LM, build_dataset
    from .lmdata import random_pairs, lesson_pairs
    from .lmtrain import split, vocab_from
    from .synth import render
    import copy
    lm = cand.load_lm() or LM(H=384); rnd = cand.state.get("lm_round", 0); snap = copy.deepcopy((lm.P, lm.toks, lm.words, lm.H)); n0 = lm.n_params()
    n_pairs = int(os.environ.get("NUWAA_LM_PAIRS", 6000 if cand.ram_ok(600 << 20) else 1500))                                       # a phone with little free memory trains on less
    pairs = random_pairs(n_pairs, seed=100 + rnd)
    own = [(d, render(s["expr"], cand.lib)) for s in cand.lib.skills.values() if s["id"] not in {t["id"] for t in cur.LESSONS} for d in s.get("desc", []) if d]
    pairs += (lesson_pairs(cur.LESSONS, cand.lib) + own) * 3
    tr, _ = split(pairs); toks, words = vocab_from(tr, 1, 1); new_t, new_w = lm.add_vocab(toks, words)
    val = build_dataset(lm, _lm_val_pairs()); before = lm.perplexity(*val)
    X, Y, EX, PW = build_dataset(lm, tr)
    need = lm.nbytes() * 4 + len(Y) * 120
    if not cand.ram_ok(need): keep = max(2000, int(len(Y) * cand.ram_available() * .4 / max(1, len(Y) * 120)) // 2); X, Y, EX = X[:keep], Y[:keep], EX[:keep]
    lm.fit(X, Y, EX, PW, epochs=3 if mode == "develop" else 2, lr=5e-4, say=lambda *_: None)
    after = lm.perplexity(*val); note = ""
    if (before - after) / before < 0.03 and lm.H < 2048 and cand.ram_ok(lm.nbytes() * 8):         # stalled: make the network bigger, then keep training
        lm.widen(96); lm.fit(X, Y, EX, PW, epochs=2, lr=5e-4, say=lambda *_: None); after = lm.perplexity(*val); note = f", widened to H={lm.H}"
    if after > before - 1e-9:                                           # no real gain on never-trained programs: keep the OLD weights, never save a worse brain
        lm.P, lm.toks, lm.words, lm.H = snap; lm._index(); lm.opt = None; note += " (no gain: kept the old weights)"; after = before
    cand.state["lm_round"] = rnd + 1; lm.save(cand.lm_path())
    return f"weights: val_ppl {before:.3f} -> {after:.3f}, params {n0} -> {lm.n_params()}{note}"

def _compress(m, say=print, max_new=3):
    """Library learning: a pipeline f(g(h(x))) that appears 2+ times across skills becomes ONE new skill (shorter future searches)."""
    from .synth import evaluate, type_of
    from .verify import fuzz_inputs
    table = m.lib.table(); chains = {}
    def walk(e):
        if e[0] in ("x", "c"): return
        if len(e) == 2:
            ch = [e[0]]; node = e[1]
            while len(node) == 2 and node[0] not in ("x", "c"): ch.append(node[0]); node = node[1]
            if len(ch) >= 2 and node[0] == "x": chains[tuple(ch)] = chains.get(tuple(ch), 0) + 1
        for c in e[1:]: walk(c)
    for s in list(m.lib.skills.values()): walk(s["expr"])
    added = []
    for ch, n in sorted(chains.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0])):
        if n < 2 or len(added) >= max_new: continue
        expr = ("x",)
        for name in reversed(ch): expr = (name, expr)
        if any(s["expr"] == expr for s in m.lib.skills.values()): continue
        t_in = table[ch[-1]][0][0]; sid = "pipe_" + "_".join(c.replace("skill:", "") for c in reversed(ch))[:48]
        good = [(i, o) for i in fuzz_inputs(t_in, 7, 10) for o in [evaluate(expr, (i,), m.lib, table)] if o is not None]
        if len(good) < 5: continue
        skill = {"id": sid, "in_types": [t_in], "out_type": type_of(good[0][1]), "expr": expr, "level": 9, "n_cases": len(good),
                 "desc": ["مسار مركّب: " + " ثم ".join(reversed(ch)), "pipeline: " + " then ".join(reversed(ch))]}
        ok, _ = verify_skill(skill, m.lib, [[i, o] for i, o in good])
        if ok: m.lib.skills[sid] = skill; table = m.lib.table(); added.append(sid)
    return added

def _run(root, mode, approve, say=print, consume=True):
    root = Path(root)
    if consume: consume_press(root / PRESS)                          # PermissionError unless a human pressed the button
    base = Mind(root); rec = {"mode": mode, "approve": bool(approve)}
    if mode == "develop":
        gate = base.competence(); rec["gate"] = {k: gate[k] for k in ("exam", "skills", "reasons")}
        if not gate["allowed"]:
            rec.update(decision="blocked", message="ممنوع: النموذج ما يعرف البرمجة بعد. اضغط «تعلّم الأساسيات» أولا. " + " | ".join(gate["reasons"])); return _log(root, rec, say)
    before = metrics(base, root); rec["before"] = before
    tmp = Path(tempfile.mkdtemp(prefix="nuwaa_mind_")); shutil.copytree(base.dir, tmp / "learned", dirs_exist_ok=True)
    cand = Mind(root, tmp / "learned"); actions = []
    # 1) words: build vocabulary from the data (+ what users asked and it did not understand)
    corpus = cand.read_corpus(); texts = [t for _, t in corpus] + cand.inbox_texts() + [d for s in cand.lib.skills.values() for d in s.get("desc", [])]
    actions.append(f"words: +{cand.learn_words(texts)} merges")
    if not cand.nb["docs"]: cand.learn_topics(corpus); actions.append("topics: learned")
    # 2) programming: what you taught it by examples, then the next lesson level
    for w in list(cand.wishlist):
        ok, info = cand.learn_task(w, 7, 3000000, 240); actions.append(f"wish {w['id']}: {'learned' if ok else 'FAILED - ' + info.get('why', '')}")
        if ok: cand.wishlist = [x for x in cand.wishlist if x["id"] != w["id"]]
    # 3) building blocks from code you uploaded (verified one by one) - develop only
    if mode == "develop":
        from . import codelearn
        inbox = cand.dir / "code_inbox"
        for f in sorted(inbox.glob("*.txt"))[:50] if inbox.exists() else []:
            new, notes = codelearn.propose(f.read_text(encoding="utf-8"), cand.lib, origin=f.name)
            for o in new:
                if len(cand.lib.ops) < 300: cand.lib.ops[o["name"]] = o
            actions.append(f"code {f.name}: +{len(new)} ops ({'; '.join(notes)[:150]})"); f.unlink()
    top = 2 if mode == "study" else cand.state.get("level", 0) + 1
    levels = [1, 2] if mode == "study" else [top]
    for t in cur.LESSONS:
        if t["level"] in levels and t["id"] not in cand.lib.skills:
            ok, info = cand.learn_task(t, 7, 3000000, 240); actions.append(f"lesson {t['id']}: {'learned' if ok else 'FAILED - ' + info.get('why', '')}")
    if all(t["id"] in cand.lib.skills for t in cur.LESSONS if t["level"] in levels): cand.state["level"] = max(cand.state.get("level", 0), max(levels))
    if mode == "develop":
        if top > max(t["level"] for t in cur.LESSONS):                       # the teacher ran out of lessons: invent practice problems by itself
            from . import selfplay
            actions.append("selfplay: " + (", ".join(selfplay.run(cand, say=say)) or "nothing new"))
    if mode == "develop": actions.append("compress: " + (", ".join(_compress(cand, say)) or "nothing new"))
    actions.append(lm_step(cand, mode, say))
    cand.save(); rec["actions"] = actions
    # 3) verify EVERYTHING again from scratch (regression), then compare
    bad = []
    for s in cand.lib.skills.values():
        lesson = next((t for t in cur.LESSONS if t["id"] == s["id"]), None)
        ok, why = verify_skill(s, cand.lib, (lesson["examples"] + lesson["holdout"]) if lesson else [])
        if not ok: bad.append(f"{s['id']}: {why[:1]}")
    after = metrics(cand, root); rec["after"] = after; reasons = []
    if bad: reasons.append("skills failed re-verification: " + "; ".join(bad))
    if cand.size_bytes() > cand.budget_bytes(): reasons.append(f"exceeds size budget ({cand.size_bytes()} > {cand.budget_bytes()} bytes)")
    worse = [k for k in before if after[k] < before[k] - 1e-9]; better = [k for k in before if after[k] > before[k] + 1e-9]
    if worse: reasons.append("got worse in: " + ", ".join(worse))
    if not better: reasons.append("nothing got strictly better")
    rec["reasons"] = reasons
    if reasons: rec["decision"] = "kept previous"
    elif not approve: rec["decision"] = "better, but you did not approve: nothing changed"
    else:
        vs = VersionStore(root / "versions_mind"); vid = vs.snapshot(str(base.dir), f"before {mode}", "validator+human")   # old version kept, hash-verified
        old = root / "learned.old"; shutil.rmtree(old, ignore_errors=True); base.dir.rename(old); shutil.copytree(tmp / "learned", base.dir); shutil.rmtree(old, ignore_errors=True)
        rec["decision"] = "accepted"; rec["rollback_to"] = vid
    shutil.rmtree(tmp, ignore_errors=True); return _log(root, rec, say)

def study(root=".", approve=False, say=print): return _run(root, "study", approve, say)
def develop(root=".", approve=False, say=print, rounds=1, max_minutes=120):
    """One button press = one SESSION of up to `rounds` cycles (hard cap 20, time cap). It stops by itself as soon as a round brings no improvement.
    To go on after that, press again: the permission never becomes permanent."""
    rounds = max(1, min(int(rounds), 20)); t0 = time.time(); rec = _run(root, "develop", approve, say, consume=True)
    for i in range(1, rounds):
        if rec.get("decision") != "accepted" or time.time() - t0 > max_minutes * 60: break
        rec = _run(root, "develop", approve, say, consume=False)
    return rec

def button(root=".", approve=True, rounds=3, say=print):
    """The ONE visible button. A human click = a bounded session: if the mind does not know programming yet it is taught the basics first (the teacher decides what, not the mind),
    then it develops itself for up to `rounds` cycles. Every stage still needs its own single-use press, made by the authenticated admin action."""
    press(root, "button")
    if not Mind(root).competence()["allowed"]:
        rec = study(root, approve, say); press(root, "button")
        if not Mind(root).competence()["allowed"] and rec.get("decision") != "accepted": return rec
    return develop(root, approve, say, rounds=rounds)

def rollback(root="."):
    root = Path(root); vs = VersionStore(root / "versions_mind"); cur_id = vs.current()
    if not cur_id or not vs.verify(cur_id): raise RuntimeError("no verified snapshot")
    d = root / "versions_mind" / cur_id; shutil.rmtree(root / "learned", ignore_errors=True); shutil.copytree(d, root / "learned"); return cur_id

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["press", "study", "develop", "button", "rollback"]); ap.add_argument("--approve", action="store_true"); ap.add_argument("--root", default="."); ap.add_argument("--rounds", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "press": press(a.root, "cli"); print("press recorded")
    elif a.cmd == "rollback": print("restored", rollback(a.root))
    else:
        try: study(a.root, a.approve) if a.cmd == "study" else button(a.root, a.approve, a.rounds) if a.cmd == "button" else develop(a.root, a.approve, rounds=a.rounds)
        except PermissionError as e: print("OFF:", e, "(run: python -m nuwaa.mind.develop press)"); sys.exit(1)
