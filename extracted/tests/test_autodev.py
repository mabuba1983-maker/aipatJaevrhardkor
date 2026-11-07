import sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.lm import autodev as ad

class Accepts(unittest.TestCase):
    def test_accepts_when_nothing_drops(self):
        ok, d = ad.accepts({"a": 0.5, "b": 0.3}, {"a": 0.52, "b": 0.3}, tolerance=0.08)
        self.assertTrue(ok)
    def test_rejects_when_one_skill_drops_too_much(self):
        # this is exactly the real regression we measured: pairs improved while review and trace fell sharply
        ok, d = ad.accepts({"pairs": 0.80, "review": 0.10, "files": 0.37}, {"pairs": 0.84, "review": 0.0, "files": 0.37}, tolerance=0.08)
        self.assertFalse(ok); self.assertGreater(d["review"]["drop"], 0.08); self.assertLessEqual(d["pairs"]["drop"], 0)
    def test_small_drop_within_tolerance_is_accepted(self):
        ok, d = ad.accepts({"a": 1.0}, {"a": 0.93}, tolerance=0.08)
        self.assertTrue(ok)
    def test_a_skill_at_zero_before_can_only_improve_or_stay(self):
        ok, d = ad.accepts({"a": 0.0}, {"a": 0.0}, tolerance=0.08); self.assertTrue(ok)
        ok, d = ad.accepts({"a": 0.0}, {"a": 0.2}, tolerance=0.08); self.assertTrue(ok)

class RunLoop(unittest.TestCase):
    """The orchestration logic (accept -> keep going from the new best; reject -> roll back and lower lr) tested with FAKE measure/train so it
    runs in milliseconds, independent of whether real training happens to help or hurt on this particular run."""
    def test_rejected_round_restores_the_previous_weights(self):
        import numpy as np
        class FakeLM:
            def __init__(self): self.P = {"w": np.array([1.0, 2.0])}
            def save(self, path): pass
        lm = FakeLM()
        seq = iter([{"pairs": 0.5}, {"pairs": 0.6}, {"pairs": 0.1}])   # round1 improves, round2 crashes
        from nuwaa.lm.gru import GRULM
        old_measure, old_one_round, old_load = ad.measure, ad.one_round, GRULM.load
        ad.measure = lambda lm, seed=1, sizes=None: next(seq)
        ad.one_round = lambda lm, texts, minutes, lr, seed: lm.P.__setitem__("w", lm.P["w"] + 1)
        GRULM.load = staticmethod(lambda path: lm)
        try:
            import nuwaa.lm.corpus as corpus
            old_pairs = corpus.all_pairs; corpus.all_pairs = lambda root: [("q", "a")]
            try:
                n, hist = ad.run("x", tempfile.mktemp(), rounds=2, minutes_per_round=0.001, lr=1e-3, tolerance=0.08)
            finally: corpus.all_pairs = old_pairs
        finally: ad.measure, ad.one_round, GRULM.load = old_measure, old_one_round, old_load
        self.assertEqual(n, 1); self.assertTrue(hist[0]["accepted"]); self.assertFalse(hist[1]["accepted"])
        self.assertEqual(list(lm.P["w"]), [2.0, 3.0])   # one accepted +1, the rejected second +1 was rolled back

class ModuleWiring(unittest.TestCase):
    def test_skills_bench_has_all_four_skills(self):
        from nuwaa.lm import skills_bench as sb
        self.assertEqual(set(sb.SKILLS) | {"pairs"}, {"pairs", "files", "review", "arabic"})
    def test_cli_help_runs(self):
        import subprocess
        r = subprocess.run([sys.executable, "-m", "nuwaa.lm.autodev", "--help"], cwd=str(ROOT), capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0); self.assertIn("--tolerance", r.stdout)

if __name__ == "__main__": unittest.main()
