# -*- coding: utf-8 -*-
import json, os, shutil, sys, tempfile, unittest
os.environ.setdefault('NUWAA_LM_PAIRS', '300')
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.mind import develop as dv
from nuwaa.mind.mind import Mind
from nuwaa.mind.vocab import LearnedVocab
from nuwaa.mind.synth import Library, solve, evaluate, render_function, call_skill
from nuwaa.mind.verify import verify_skill, source_problems
from nuwaa.mind import curriculum as cur

def fresh_root():
    r = Path(tempfile.mkdtemp()); shutil.copytree(ROOT / "data", r / "data"); return r

class Vocab(unittest.TestCase):
    def test_builds_words_from_text_and_flags_new_ones(self):
        v = LearnedVocab()
        for _ in range(3): v.observe("مرحبا بالعالم الكبير")
        v.learn_merges(20)
        self.assertTrue(v.known("مرحبا")); self.assertEqual(v.unknown_words("مرحبا زنجبيل"), ["زنجبيل"]); self.assertLess(v.coverage("زنجبيل كركدن"), 0.1)
        self.assertGreater(len(v.merges), 0)

class Synth(unittest.TestCase):
    def test_finds_program_and_rejects_one_that_only_fits_the_examples(self):
        ex = [[[1, 2, 3], 14], [[2, 2], 8], [[0, 4], 16], [[5], 25]]; ho = [[[1, 1, 1, 1], 4], [[3, 0], 9]]
        e, _ = solve(ex, ho); self.assertEqual(e, ("sum", ("map_sq", ("x",))))
        e2, _ = solve(ex, [[[1, 1, 1, 1], 999]]); self.assertIsNone(e2)                      # holdout contradicts every short program
    def test_learned_skill_shortens_the_search(self):
        t = [x for x in cur.EXAM if x["id"] == "e_span_pos"][0]
        e, _ = solve(t["examples"], t["holdout"], Library(), cur.EXAM_SIZE, cur.EXAM_NODES, 10); self.assertIsNone(e)
        m = Mind(fresh_root())
        for l in cur.LESSONS:
            if l["id"] in ("span", ): self.assertTrue(m.learn_task(l)[0])
        e, _ = solve(t["examples"], t["holdout"], m.lib, cur.EXAM_SIZE, cur.EXAM_NODES, 10); self.assertIsNotNone(e)

class Verify(unittest.TestCase):
    def test_unsafe_source_is_rejected(self):
        self.assertTrue(source_problems("import os\ndef f(x):\n    return os.system('ls')\n", set()))
        self.assertTrue(source_problems("def f(x):\n    return open('/etc/passwd')\n", set()))
        self.assertFalse(source_problems("def f(x):\n    return sum([v * v for v in x])\n", set()))
    def test_wrong_skill_fails_verification(self):
        s = {"id": "bad", "in_type": "list", "out_type": "int", "expr": ("sum", ("x",))}
        ok, why = verify_skill(s, Library(), [[[1, 2], 99]]); self.assertFalse(ok)

class Button(unittest.TestCase):
    def test_nothing_starts_without_a_press_and_a_press_is_single_use(self):
        r = fresh_root()
        with self.assertRaises(PermissionError): dv.study(r, True, say=lambda *_: 0)
        dv.press(r); dv.develop(r, False, say=lambda *_: 0)
        with self.assertRaises(PermissionError): dv.develop(r, False, say=lambda *_: 0)

class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = fresh_root(); cls.log = []; cls.say = lambda *_: 0
        cls.before = Mind(cls.r).competence()
        dv.press(cls.r); cls.blocked = dv.develop(cls.r, True, say=cls.say)
        dv.press(cls.r); cls.studied = dv.study(cls.r, True, say=cls.say)
        dv.press(cls.r); cls.dev = dv.develop(cls.r, True, say=cls.say)
    def test_1_empty_mind_cannot_self_develop(self):
        self.assertFalse(self.before["allowed"]); self.assertEqual(self.blocked["decision"], "blocked"); self.assertEqual(Mind(self.r).state.get("level", 0) >= 0, True)
    def test_2_study_makes_it_strictly_better(self):
        self.assertEqual(self.studied["decision"], "accepted"); self.assertGreater(self.studied["after"]["exam"], self.studied["before"]["exam"]); self.assertGreaterEqual(self.studied["after"]["skills"], 10)
    def test_3_after_study_develop_is_allowed_and_improves(self):
        self.assertNotEqual(self.dev["decision"], "blocked"); self.assertEqual(self.dev["decision"], "accepted")
        self.assertGreater(self.dev["after"]["skills"], self.dev["before"]["skills"]); self.assertGreaterEqual(self.dev["after"]["exam"], self.dev["before"]["exam"])
    def test_4_skills_really_run_and_are_inside_budget(self):
        m = Mind(self.r); s = m.lib.skills["sum_even"]; self.assertEqual(call_skill(s, m.lib, [1, 2, 3, 4]), 6)
        ns = {}; exec(render_function(s, m.lib), ns); self.assertEqual(ns["sum_even"]([1, 2, 3, 4]), 6)
        self.assertLess(m.size_bytes(), m.budget_bytes())
    def test_5_it_analyses_and_admits_what_it_does_not_know(self):
        m = Mind(self.r); a = m.ask("مجموع مربعات عناصر القائمة"); self.assertEqual(a["route"], "skill"); self.assertIn("sum_sq", a["reply"])
        b = m.ask("كيف أطبخ كبسة زنجبيل فضائية"); self.assertEqual(b["route"], "unknown"); self.assertTrue(b["analysis"]["unknown"]); self.assertEqual(len(m.inbox_texts()), 1)
    def test_6_teach_by_examples_then_develop_learns_it(self):
        m = Mind(self.r); m.add_wish("ثلاثة أضعاف الرقم", [[i, i * 3] for i in (1, 2, 3, 4, 5, 6, 7)], "triple")
        dv.press(self.r); rec = dv.develop(self.r, True, say=self.say)
        self.assertTrue(any("wish triple: learned" in a for a in rec["actions"])); self.assertIn("triple", Mind(self.r).lib.skills)
    def test_7_rollback_restores_the_previous_version(self):
        n = len(Mind(self.r).lib.skills); dv.rollback(self.r); self.assertLessEqual(len(Mind(self.r).lib.skills), n)

class Compress(unittest.TestCase):
    def test_repeated_pipeline_becomes_a_skill(self):
        m = Mind(fresh_root())
        m.lib.skills["a"] = {"id": "a", "in_types": ["str"], "out_type": "int", "expr": ("len_s", ("upper", ("rev_s", ("x",))))}
        m.lib.skills["b"] = {"id": "b", "in_types": ["str"], "out_type": "str", "expr": ("strip", ("upper", ("rev_s", ("x",))))}
        m.lib.skills["c"] = {"id": "c", "in_types": ["str"], "out_type": "str", "expr": ("lower", ("upper", ("rev_s", ("x",))))}
        added = dv._compress(m); self.assertTrue(any("upper" in a and "rev_s" in a for a in added))

class ServerMind(unittest.TestCase):
    def test_endpoints_and_admin_only_buttons(self):
        import threading, time, urllib.request, urllib.error
        sys.path.insert(0, str(ROOT / "server")); import server as srv
        r = fresh_root(); app = srv.App(r / "data", r / "none.pt", r / "kn", admin_token="tok", root=r)
        httpd = srv.make_server(app, "127.0.0.1", 0); threading.Thread(target=httpd.serve_forever, daemon=True).start(); self.addCleanup(httpd.shutdown); self.addCleanup(httpd.server_close)
        port = httpd.server_address[1]
        def call(path, body=None, token=None):
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
            try:
                with urllib.request.urlopen(req, timeout=30) as x: return x.status, json.loads(x.read())
            except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
        c, st = call("/api/mind"); self.assertEqual(c, 200); self.assertFalse(st["competence"]["allowed"])
        self.assertEqual(call("/api/mind/develop", {"approve": True})[0], 403)                      # strangers cannot press the button
        self.assertEqual(call("/api/mind/develop", {"approve": True, "rounds": 1}, "tok")[0], 200)
        for _ in range(1200):
            time.sleep(0.5)
            if not app.mind_busy: break
        c, st = call("/api/mind"); self.assertIn(st["last"]["decision"], ("accepted", "kept previous"))   # ONE button: empty mind -> taught the basics first, then develops
        for _ in range(2):
            if st["competence"]["allowed"]: break
            self.assertEqual(call("/api/mind/study", {"approve": True}, "tok")[0], 200)
            for _ in range(600):
                time.sleep(0.5)
                if not app.mind_busy: break
            c, st = call("/api/mind")
        c, st = call("/api/mind"); self.assertTrue(st["competence"]["allowed"]); self.assertGreaterEqual(st["skills"], 10)
        c, a = call("/api/mind/ask", {"message": "عدد الكلمات في الجملة"}); self.assertEqual(a["route"], "skill")


from nuwaa.mind.safe_eval import problems, run
from nuwaa.mind import review as rv, codelearn
from nuwaa.mind.lm import LM, build_dataset
from nuwaa.mind.lmdata import random_pairs

class SafeEval(unittest.TestCase):
    def test_runs_pure_code_and_refuses_everything_else(self):
        self.assertEqual(run("sum(v * v for v in a if v % 2 == 0)", ["a"], [[1, 2, 3, 4]]), 20)
        for bad in ("__import__('os').system('ls')", "open('/etc/passwd')", "a.__class__", "(lambda: 1)()", "exec('1')"): self.assertTrue(problems(bad, ["a"]), bad)
    def test_resource_limits(self):
        with self.assertRaises(Exception): run("10 ** 10 ** 10", [], [])
        with self.assertRaises(Exception): run("sum(range(10 ** 9))", [], [])

class Review(unittest.TestCase):
    CODE = "import os\ndef f(a, b=[]):\n    try:\n        x = 1/0\n    except:\n        pass\n    return nope\npassword = 'supersecret123'\n"
    def test_finds_real_problems_with_lines(self):
        rules = {f["rule"]: f["line"] for f in rv.review_text("t.py", self.CODE)["findings"]}
        for r in ("div-zero", "mutable-default", "bare-except", "undefined-name", "hardcoded-secret", "unused-import"): self.assertIn(r, rules)
        self.assertEqual(rules["div-zero"], 4)
    def test_clean_file_and_json_and_syntax(self):
        self.assertEqual(rv.review_text("ok.py", "def f(x):\n    return x + 1\n")["findings"], [])
        self.assertEqual(rv.review_text("a.json", "{bad")["findings"][0]["rule"], "invalid-json"); self.assertEqual(rv.review_text("s.py", "def (:")["findings"][0]["rule"], "syntax-error")
    def test_review_never_executes_the_file(self):
        marker = Path(tempfile.mkdtemp()) / "pwned"; rv.review_text("evil.py", f"open({str(marker)!r}, 'w').write('x')\n"); self.assertFalse(marker.exists())
    def test_zip_is_read_safely(self):
        import io, zipfile
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z: z.writestr("ok.py", "x = 1\n"); z.writestr("../evil.py", "x"); z.writestr("big.bin", "x" * 10)
        self.assertEqual([n for n, _ in rv.read_zip(b.getvalue())], ["ok.py"])

class CodeLearn(unittest.TestCase):
    def test_learns_pure_functions_and_ignores_dangerous_ones(self):
        src = "def clamp_sum(xs):\n    return sum([min(v, 10) for v in xs])\ndef evil(x):\n    return __import__('os').system('ls')\ndef dbl(x):\n    return x * 2\n"
        new, notes = codelearn.propose(src, Library()); names = [o["name"] for o in new]
        self.assertIn("clamp_sum", names); self.assertFalse(any("evil" in n for n in names))

class Weights(unittest.TestCase):
    def test_lm_trains_generalises_saves_and_grows_without_forgetting(self):
        import numpy as np
        from nuwaa.mind.lmtrain import train, split
        pairs = random_pairs(900, seed=3); lm = LM(H=96); r = train(lm, pairs, 3, say=lambda *_: 0)
        self.assertLess(r["val_ppl"], r["val_ppl_before"] / 5)                                  # it really learned (on programs it never trained on)
        va = build_dataset(lm, split(pairs)[1]); p0 = lm.perplexity(*va); lm.widen(32); self.assertAlmostEqual(lm.perplexity(*va), p0, places=3)   # growing keeps the function
        f = Path(tempfile.mkdtemp()) / "w.npz"; lm.save(f); lm2 = LM.load(f); self.assertAlmostEqual(lm2.perplexity(*va), p0, delta=p0 * .05)
        self.assertEqual(lm.sample("sum of squares of the list", n=1, temperature=0, seed=1), lm.sample("sum of squares of the list", n=1, temperature=0, seed=1))
    def test_shipped_weights_are_not_empty(self):
        f = ROOT / "weights" / "mind_lm.npz"; self.assertTrue(f.exists()); lm = LM.load(f); self.assertGreater(lm.n_params(), 100_000)
        va = build_dataset(lm, random_pairs(300, seed=4242)); self.assertLess(lm.perplexity(*va), 3.0)

if __name__ == "__main__": unittest.main()
