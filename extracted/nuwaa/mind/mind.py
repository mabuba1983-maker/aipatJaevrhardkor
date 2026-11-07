# -*- coding: utf-8 -*-
"""The Mind: a small engine that LEARNS (words, topics, programming skills), ANALYSES what it is asked, and knows what it does not know.
Everything it learns lives in one folder (`learned/`) as plain data, so it can be measured, size-limited, versioned and rolled back."""
import json, math, os, re, shutil, time
from collections import Counter
from pathlib import Path
from .vocab import LearnedVocab, words
from .synth import Library, solve, type_of, render_function, call_skill, size as expr_size
from .verify import verify_skill
from . import curriculum as cur

TOPIC_FILES = {"code": ("python_chat", "generated_python", "code_basics", "code_langs"), "chat": ("arabic_chat", "generated_arabic", "instructions_ar")}

class Mind:
    def __init__(self, root=".", learned=None):
        self.root = Path(root); self.dir = Path(learned) if learned else self.root / "learned"; self.dir.mkdir(parents=True, exist_ok=True)
        self.vocab = LearnedVocab.load(self.dir / "vocab.json"); self.nb = self._load("nb.json", {"docs": {}, "tok": {}})
        self.lib = Library(self._load("skills.json", []), self._load("ops.json", [])); self.state = self._load("state.json", {"level": 0})
        self.wishlist = self._load("wishlist.json", [])
    def _load(self, name, default):
        p = self.dir / name; return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    def save(self):
        self.vocab.save(self.dir / "vocab.json")
        for name, obj in (("nb.json", self.nb), ("skills.json", list(self.lib.skills.values())), ("ops.json", list(self.lib.ops.values())), ("state.json", self.state), ("wishlist.json", self.wishlist)):
            (self.dir / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    # ---------- size ----------
    def size_bytes(self): return sum(f.stat().st_size for f in self.dir.rglob("*") if f.is_file())
    def budget_bytes(self):
        p = self.root / "mind_budget.json"                       # a human can change it; default 2 GB of disk. RAM is guarded separately (ram_ok)
        return int(json.loads(p.read_text())["mb"] * 1024 * 1024) if p.exists() else 2048 * 1024 * 1024
    @staticmethod
    def ram_available():
        try:
            with open("/proc/meminfo") as f:
                for l in f:
                    if l.startswith("MemAvailable"): return int(l.split()[1]) * 1024
        except OSError: pass
        return 1 << 30
    def ram_ok(self, need_bytes, fraction=0.5): return need_bytes < self.ram_available() * fraction
    # ---------- the neural weights ----------
    def lm_path(self): return self.dir / "mind_lm.npz"
    def load_lm(self):
        from .lm import LM
        if not self.lm_path().exists():
            seed = self.root / "weights" / "mind_lm.npz"                   # the pre-trained weights that ship with the app
            if seed.exists(): shutil.copy(seed, self.lm_path())
        return LM.load(self.lm_path()) if self.lm_path().exists() else None
    def lm_propose(self, task, n=60):
        """The neural model WRITES candidate programs from the description; each is run on the examples AND the hidden cases. Returns source or None."""
        from .safe_eval import problems, run
        lm = self.load_lm()
        if lm is None: return None
        ar = task.get("arity", 1); params = ["x", "y"][:ar]; rows = task["examples"] + task["holdout"]; seen = set()
        for k, d in enumerate((task.get("desc_en", ""), task.get("desc_ar", ""))):
            if not d: continue
            for temp in (0.0, 0.5, 0.9):
                for src in lm.sample(d, n=1 if temp == 0 else n, temperature=temp, seed=k * 7 + int(temp * 10)):
                    src = src.strip()
                    if src in seen or not src or problems(src, params): continue
                    seen.add(src)
                    try: ok = all(run(src, params, list(i) if ar > 1 else [i]) == o for i, o in rows)
                    except Exception: ok = False
                    if ok: return src
        return None
    def _install_lm_program(self, task, src):
        from .synth import type_of
        from .verify import verify_op
        ar = task.get("arity", 1); ex = task["examples"][0]; ins = list(ex[0]) if ar > 1 else [ex[0]]
        op = {"name": "lm_" + re.sub(r"\W", "_", task["id"])[:40], "args": [type_of(v) for v in ins], "ret": type_of(ex[1]), "params": ["x", "y"][:ar], "src": src, "origin": "lm"}
        ok, why = verify_op(op)
        if not ok: return False, {"why": "lm op rejected: " + "; ".join(why)}
        self.lib.ops[op["name"]] = op
        skill = {"id": task["id"], "in_types": op["args"], "out_type": op["ret"], "expr": ("op:" + op["name"],) + tuple(("x",) if i == 0 else ("y",) for i in range(ar)),
                 "desc": [task.get("desc_ar", ""), task.get("desc_en", "")], "level": task.get("level", 0), "n_cases": len(task["examples"]) + len(task["holdout"]), "by": "neural"}
        ok, why = verify_skill(skill, self.lib, task["examples"] + task["holdout"])
        if not ok: del self.lib.ops[op["name"]]; return False, {"why": "; ".join(why)}
        self.lib.skills[skill["id"]] = skill; return True, {"by": "neural", "src": src}
    # ---------- learning words and topics ----------
    def read_corpus(self, data_dir=None):
        """(topic, text) from data/ ; data/eval is never read (it is the test)."""
        d = Path(data_dir or self.root / "data"); out = []
        for f in sorted(d.glob("*.jsonl")) + sorted(d.glob("*.txt")):
            topic = next((t for t, names in TOPIC_FILES.items() if f.stem in names), "chat")
            if f.suffix == ".jsonl":
                for l in f.read_text(encoding="utf-8").splitlines():
                    try: j = json.loads(l); out.append((topic, j["user"] + " " + j["bot"]))
                    except Exception: pass
            else: out += [(topic, c) for c in f.read_text(encoding="utf-8").split("\n\n") if c.strip()]
        return out
    def learn_words(self, texts, grow=300, cap=3000):
        """Rebuilt FROM SCRATCH from all the text every time (never counts the same text twice, so 'knowing more words' can't be faked)."""
        old = len(self.vocab.merges); v = LearnedVocab()
        for t in texts: v.observe(t)
        v.learn_merges(min(cap, old + grow)); self.vocab = v; return len(v.merges) - old
    def learn_topics(self, corpus):
        for topic, text in corpus:
            self.nb["docs"][topic] = self.nb["docs"].get(topic, 0) + 1
            for tk in self.vocab.encode(text):
                c = self.nb["tok"].setdefault(tk, {}); c[topic] = c.get(topic, 0) + 1
        self.nb["tok"] = {k: v for k, v in self.nb["tok"].items() if sum(v.values()) >= 2}
    def topic(self, text):
        topics = list(self.nb["docs"]) or ["chat"]; total = sum(self.nb["docs"].values()) or 1; V = len(self.nb["tok"]) + 1
        sums = {t: sum(c.get(t, 0) for c in self.nb["tok"].values()) for t in topics}; lp = {}
        for t in topics:
            lp[t] = math.log((self.nb["docs"].get(t, 0) + 1) / (total + len(topics)))
            for tk in self.vocab.encode(text): lp[t] += math.log((self.nb["tok"].get(tk, {}).get(t, 0) + 1) / (sums[t] + V))
        m = max(lp.values()); z = sum(math.exp(v - m) for v in lp.values()); return {t: round(math.exp(v - m) / z, 3) for t, v in lp.items()}
    # ---------- learning programs ----------
    def learn_task(self, task, max_size=7, max_nodes=400000, max_seconds=60):
        """Search a program, then verify it 3 ways. The skill is added to the library ONLY if all checks pass."""
        try:
            ar = task.get("arity", 1)
            e, st = solve(task["examples"], task["holdout"], self.lib, 5, 60000, 10, ar)                 # 1) quick search
            if e is None:
                src = self.lm_propose(task)                                                              # 2) the neural weights try to write it
                if src:
                    ok, info = self._install_lm_program(task, src)
                    if ok: return True, info
                e, st = solve(task["examples"], task["holdout"], self.lib, max_size, max_nodes, max_seconds, ar)   # 3) long careful search
            if e is None: return False, {"why": "no program found within budget", **st}
            ex = task["examples"][0]; ins = list(ex[0]) if ar > 1 else [ex[0]]
            skill = {"id": task["id"], "in_types": [type_of(v) for v in ins], "out_type": type_of(ex[1]), "expr": e, "desc": [task.get("desc_ar", ""), task.get("desc_en", "")],
                                               "level": task.get("level", 0), "n_cases": len(task["examples"]) + len(task["holdout"])}
        except Exception as err: return False, {"why": f"bad task: {type(err).__name__}: {err}"}
        ok, why = verify_skill(skill, self.lib, task["examples"] + task["holdout"])
        if not ok: return False, {"why": "; ".join(why)}
        self.lib.skills[skill["id"]] = skill; return True, {"expr_size": expr_size(e), **st}
    def add_wish(self, desc, examples, tid=None, arity=1):
        """Teach a new programming task by examples: [[input, output], ...] (>=5; the last ~20% are hidden for checking)."""
        if not (isinstance(examples, list) and len(examples) >= 5): raise ValueError("need at least 5 examples")
        k = max(1, len(examples) // 5); tid = tid or "w_" + str(abs(hash(desc)) % 10 ** 6)
        ar = 2 if isinstance(examples[0][0], list) and len(examples[0][0]) == 2 and arity == 2 else 1
        task = {"id": re.sub(r"\W", "_", tid), "level": 9, "arity": ar, "desc_ar": desc, "desc_en": desc, "examples": examples[:-k], "holdout": examples[-k:]}
        for v in (list(examples[0][0]) if ar == 2 else [examples[0][0]]) + [examples[0][1]]: type_of(v)         # raises if unsupported
        self.wishlist = [w for w in self.wishlist if w["id"] != task["id"]] + [task]; self.save(); return task["id"]
    def exam(self, max_size=cur.EXAM_SIZE, max_nodes=cur.EXAM_NODES):
        res = {}
        for t in cur.EXAM:
            e, _ = solve(t["examples"], t["holdout"], self.lib, max_size, max_nodes, 15, t.get("arity", 1)); res[t["id"]] = e is not None
        return {"score": round(sum(res.values()) / len(res), 3), "results": res}
    def exam_hard(self):
        """Second, harder exam (bigger problems, two inputs). Not used for the gate, only to measure real progress."""
        res = {}
        for t in cur.EXAM_HARD:
            e, _ = solve(t["examples"], t["holdout"], self.lib, cur.EXAM_SIZE + 1, cur.EXAM_NODES * 2, 20, t.get("arity", 1)); res[t["id"]] = e is not None
        return round(sum(res.values()) / len(res), 3)
    def competence(self):
        ex = self.exam(); n = len(self.lib.skills)
        reasons = ([] if ex["score"] >= cur.EXAM_PASS else [f"درجة اختبار البرمجة {ex['score']} أقل من {cur.EXAM_PASS}"]) + ([] if n >= cur.MIN_SKILLS else [f"مهاراته الموثّقة {n} أقل من {cur.MIN_SKILLS}"])
        return {"allowed": not reasons, "exam": ex["score"], "skills": n, "reasons": reasons, "results": ex["results"]}
    # ---------- analysing a request ----------
    def _skill_scores(self, text):
        q = Counter(self.vocab.encode(text)); docs = {sid: Counter(self.vocab.encode(" ".join(s.get("desc", [])))) for sid, s in self.lib.skills.items()}
        df = Counter(t for d in docs.values() for t in d); N = max(1, len(docs)); out = []
        def w(c): return {t: n * math.log(1 + N / df.get(t, 1)) for t, n in c.items()}
        qv = w(q); qn = math.sqrt(sum(v * v for v in qv.values())) or 1
        for sid, d in docs.items():
            dv = w(d); dn = math.sqrt(sum(v * v for v in dv.values())) or 1
            out.append((sum(qv[t] * dv.get(t, 0) for t in qv) / (qn * dn), sid))
        return sorted(out, reverse=True)
    def analyze(self, text):
        """A visible chain of thought: what the engine saw, what it knows, what it does NOT know."""
        ws = [w for w in words(text) if w.isalnum()]; ar = sum(1 for ch in text if "\u0600" <= ch <= "\u06ff"); la = sum(1 for ch in text if ch.isascii() and ch.isalpha())
        topic = self.topic(text) if self.nb["docs"] else {}; unk = self.vocab.unknown_words(text); cov = self.vocab.coverage(text)
        match = self._skill_scores(text)[:3] if self.lib.skills else []
        steps = [f"لغة الرسالة: {'عربية' if ar >= la else 'إنجليزية/كود'} ({len(ws)} كلمة)", f"الكلمات التي يعرفها: {round(cov * 100)}%"]
        if unk: steps.append("كلمات جديدة عليه: " + "، ".join(unk[:6]))
        if topic: steps.append("الموضوع المرجّح: " + max(topic, key=topic.get))
        if match and match[0][0] > 0: steps.append(f"أقرب مهارة برمجية: {match[0][1]} (تشابه {match[0][0]:.2f})")
        return {"coverage": round(cov, 3), "unknown": unk, "topic": topic, "skills": [{"id": s, "sim": round(v, 3)} for v, s in match], "steps": steps}
    def ask(self, text, min_sim=0.25):
        a = self.analyze(text); best = a["skills"][0] if a["skills"] else None
        if best and best["sim"] >= min_sim:
            s = self.lib.skills[best["id"]]
            return {"reply": f"عندي مهارة موثّقة ({s['n_cases']} حالة اختبار + فحص في عملية معزولة):\n\n```python\n{render_function(s, self.lib)}```", "analysis": a, "route": "skill"}
        self.log_inbox(text)
        why = ("كلماتي الجديدة: " + "، ".join(a["unknown"][:5])) if a["unknown"] else "ما عندي مهارة مطابقة"
        return {"reply": f"ما أعرف هذا بعد ({why}). سجّلته عشان أتعلمه في دورة التطوير القادمة.", "analysis": a, "route": "unknown"}
    def log_inbox(self, text):
        if len(self.inbox_texts()) >= 2000: return                      # public endpoint: never let strangers grow the file without limit
        with open(self.dir / "inbox.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps({"t": int(time.time()), "text": text[:1000]}, ensure_ascii=False) + "\n")
    def inbox_texts(self):
        p = self.dir / "inbox.jsonl"
        return [json.loads(l)["text"] for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []
    def lm_info(self):
        p = self.lm_path()
        if not p.exists() and not (self.root / "weights" / "mind_lm.npz").exists(): return None
        lm = self.load_lm(); return {"params": lm.n_params(), "hidden": lm.H, "tokens": len(lm.toks), "words": len(lm.words), "steps": lm.steps}
    def status(self):
        return {"skills": len(self.lib.skills), "level": self.state.get("level", 0), "vocab": self.vocab.stats(), "size_kb": round(self.size_bytes() / 1024, 1), "ops": len(self.lib.ops), "lm": self.lm_info(),
                "budget_mb": round(self.budget_bytes() / 1048576, 1), "wishlist": len(self.wishlist), "inbox": len(self.inbox_texts())}
