import json, os, sys, tempfile, time, unittest, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import studio

def tree():
    d = Path(tempfile.mkdtemp()) / "a" / "proj"; (d / "sub").mkdir(parents=True); (d / ".git").mkdir(); (d / "node_modules").mkdir()
    (d / "main.py").write_text("def add(a, b):\n    return a + b\n" * 6, encoding="utf-8")
    (d / "sub" / "notes.txt").write_text("الصبر مفتاح الفرج والعلم نور يهدي صاحبه. " * 5, encoding="utf-8")
    (d / ".env").write_text("API_KEY=\"abcdef123456\"\n" * 5); (d / "id_rsa.py").write_text("x = 1\n" * 30)
    (d / "leak.py").write_text("password = \"hunter2hunter2\"\nprint(1)\n" * 5)
    (d / "key.py").write_text("-----BEGIN RSA PRIVATE KEY-----\nabc\n" * 5)
    (d / "photo.jpg").write_bytes(b"\xff\xd8" * 100); (d / "doc.pdf").write_bytes(b"%PDF" * 50)
    (d / ".git" / "x.py").write_text("print('git')\n" * 20); (d / "node_modules" / "y.py").write_text("print('nm')\n" * 20)
    (d / "big.py").write_text("x = 1\n" * 300000)
    outside = Path(tempfile.mkdtemp()) / "private.py"; outside.write_text("print('private')\n" * 20, encoding="utf-8")
    try: os.symlink(outside, d / "link.py")
    except OSError: pass
    return d

class Consent(unittest.TestCase):
    def setUp(self): self.home = Path(tempfile.mkdtemp()) / "studio"; self.d = tree()
    def test_no_permission_no_reading(self):
        with self.assertRaises(PermissionError): studio.scan(self.home)
    def test_expired_permission_is_not_enough(self):
        studio.grant(self.home, self.d, days=1, now=1000.0)
        with self.assertRaises(PermissionError): studio.scan(self.home, now=1000.0 + 2 * 86400)
    def test_a_whole_disk_or_home_is_refused(self):
        for bad in ("/", str(Path.home())):
            with self.assertRaises(ValueError): studio.grant(self.home, bad)
    def test_only_programming_and_arabic_and_no_secrets_and_logged(self):
        studio.grant(self.home, self.d); st = studio.scan(self.home)
        rep = (self.home / "scan_report.txt").read_text(encoding="utf-8"); read = [l for l in rep.splitlines() if l.startswith(str(self.d.resolve()))]
        names = {Path(x).name for x in read}
        self.assertEqual(names, {"main.py", "notes.txt"})                   # not .env, id_rsa, passwords, keys, jpg, pdf, .git, node_modules, big file, outside link
        logged = [json.loads(l)["read"] for l in (self.home / "consent_log.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(logged), sorted(read)); self.assertTrue(all(Path(x).resolve().is_relative_to(self.d.resolve()) for x in logged))
        text = (self.home / "data" / "extra.txt").read_text(encoding="utf-8")
        self.assertNotIn("hunter2", text); self.assertNotIn("PRIVATE KEY", text); self.assertNotIn("'private'", text)
        self.assertGreater(st["lines"], 0); self.assertTrue(all(ord(c) < 128 or 0x621 <= ord(c) <= 0x652 or c in "ـ،؛؟«»¶\t" or ord(c) in range(0x660, 0x66A) for c in text))
    def test_revoke_stops_reading(self):
        studio.grant(self.home, self.d); studio.revoke(self.home, None)
        with self.assertRaises(PermissionError): studio.scan(self.home)

class Planning(unittest.TestCase):
    def test_two_gigabytes_is_about_five_hundred_million_weights_and_it_warns(self):
        p = studio.plan(2.0, 1_000_000)
        self.assertLess(abs(p["params"] - 500_000_000) / 500_000_000, 0.02); self.assertLess(abs(p["weights_gb"] - 2.0), 0.05)
        self.assertTrue(any("memorise" in w for w in p["warnings"]))
    def test_duty_cycle_math(self):
        self.assertAlmostEqual(studio.duty_sleep(10, 40), 15.0); self.assertEqual(studio.duty_sleep(10, 100), 0.0)
    def test_growing_keeps_the_old_behaviour(self):
        from nuwaa.lm.gru import GRULM
        home = Path(tempfile.mkdtemp()); out, p = studio.grow(home, 0.04); a = GRULM.load(str(ROOT / "weights" / "nlm2.npz")); b = GRULM.load(str(out))
        ids = a.encode("س:مرحبا\nج:أهلا\n", grow=False); self.assertAlmostEqual(a.bpc(ids), b.bpc(ids), places=3); self.assertGreater(b.n_params(), 8_000_000)

class Pack(unittest.TestCase):
    def test_pack_verify_and_tampering(self):
        root = Path(tempfile.mkdtemp()); (root / "nuwaa").mkdir(); (root / "nuwaa" / "a.py").write_text("print(1)\n"); home = Path(tempfile.mkdtemp()) / "studio"; (home / "models").mkdir(parents=True)
        (home / "models" / "current.npz").write_bytes(b"model-bytes"); (home / "consent.json").write_text("{}"); (home / "data").mkdir(); (home / "data" / "extra.txt").write_text("private code")
        out = str(Path(tempfile.mkdtemp()) / "p.zip"); studio.pack(home, out, root=root)
        names = zipfile.ZipFile(out).namelist(); self.assertIn("studio/models/current.npz", names); self.assertIn("nuwaa/a.py", names)
        self.assertNotIn("studio/consent.json", names); self.assertNotIn("studio/data/extra.txt", names)        # private material stays home unless asked
        self.assertEqual(studio.verify(out), [])
        bad = out + ".bad"
        with zipfile.ZipFile(out) as zi, zipfile.ZipFile(bad, "w") as zo:
            for n in zi.namelist(): zo.writestr(n, b"tampered" if n == "nuwaa/a.py" else zi.read(n))
        self.assertEqual(studio.verify(bad), ["nuwaa/a.py"])
    def test_press_is_single_use(self):
        from nuwaa.selfimprove.button import consume_press
        home = Path(tempfile.mkdtemp()); p = studio.press(home); consume_press(str(p))
        with self.assertRaises(PermissionError): consume_press(str(p))

class Ladder(unittest.TestCase):
    def _run(self, scores):
        home = Path(tempfile.mkdtemp()) / "studio"; (home / "models").mkdir(parents=True); (home / "models" / "current.npz").write_bytes(b"g0")
        seq = iter(scores); log = []; old_plan = studio.plan
        studio.plan = lambda *a, **k: {"params": 1, "train_memory_gb": 0.0, "chars_per_weight": 1.0, "warnings": []}
        try:
            n = {"i": 0}
            def grow(src, gb, dst): n["i"] += 1; Path(dst).write_bytes(b"g%d" % n["i"])
            done = studio.ladder(home, grow_fn=grow, train_fn=lambda: None, score_fn=lambda p: next(seq), params_fn=lambda p: 1, log=log.append)
        finally: studio.plan = old_plan
        return done, (home / "models" / "current.npz").read_bytes(), log
    def test_a_bigger_model_is_kept_only_if_it_beats_the_smaller_one(self):
        done, cur, log = self._run([2.0, 1.8, 1.8, 1.78])         # 10M: 2.0 -> 1.8 (10% better, kept) ; 40M: 1.8 -> 1.78 (1.1%: not enough)
        self.assertEqual(done, ["10M"]); self.assertEqual(cur, b"g1"); self.assertTrue(any("HALT at 40M" in l for l in log))      # restored the 10M model
    def test_it_climbs_while_every_step_helps(self):
        done, cur, log = self._run([2.0, 1.8, 1.8, 1.6, 1.6, 1.4, 1.4, 1.2, 1.2, 1.0])
        self.assertEqual(len(done), 5); self.assertEqual(cur, b"g5")
    def test_it_stops_before_a_size_that_does_not_fit(self):
        home = Path(tempfile.mkdtemp()) / "studio"; (home / "models").mkdir(parents=True); (home / "models" / "current.npz").write_bytes(b"g0"); log = []
        old = studio.plan; studio.plan = lambda *a, **k: {"params": 1, "train_memory_gb": 99.0, "chars_per_weight": 1.0, "warnings": ["the training state (99 GB) does not fit in RAM (4 GB)"]}
        try: done = studio.ladder(home, grow_fn=lambda *a: self.fail("must not grow"), train_fn=lambda: None, score_fn=lambda p: 1.0, params_fn=lambda p: 1, log=log.append)
        finally: studio.plan = old
        self.assertEqual(done, []); self.assertTrue(any("STOP before" in l for l in log))

class Engine(unittest.TestCase):
    def test_fp16_file_is_half_the_size_and_loads_back(self):
        from nuwaa.lm.gru import GRULM
        m = GRULM.load(str(ROOT / "weights" / "nlm2.npz")); d = Path(tempfile.mkdtemp()); a = d / "a.npz"; b = d / "b.npz"; m.save(str(a)); m.save(str(b), fp16=True)
        self.assertLess(b.stat().st_size, a.stat().st_size * 0.7); ids = m.encode("س:مرحبا\nج:أهلا\n", grow=False); self.assertAlmostEqual(m.bpc(ids), GRULM.load(str(b)).bpc(ids), delta=0.1)
    def test_server_can_run_a_big_model_from_any_path(self):
        d = Path(tempfile.mkdtemp()); w = d / "big.npz"; shutil_copy = __import__("shutil").copy; shutil_copy(ROOT / "weights" / "nlm2.npz", w)
        os.environ["NUWAA_WEIGHTS"] = str(w); sys.path.insert(0, str(ROOT / "server"))
        try:
            import server as srv
            app = srv.App(); r = app.reply("مرحبا"); self.assertTrue(isinstance(r, str) and r); self.assertEqual(str(app.chat().base_file), str(w))
        finally: os.environ.pop("NUWAA_WEIGHTS", None)

if __name__ == "__main__": unittest.main()
