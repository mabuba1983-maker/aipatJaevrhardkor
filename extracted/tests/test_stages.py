import json, sys, tempfile, unittest, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from nuwaa.core.stages import STAGES, ORDER, stage_config, set_stage, selected_stage
from nuwaa.core.layout import count_params, bin_size_bytes, tensor_shapes, HEADER_BYTES
from nuwaa.core.limits import phone_problems, check_phone_feasible, PhoneLimitError
from nuwaa.core.stage_gate import StageGate
from nuwaa.core.benchmark import run_benchmark, load_items
from nuwaa.core.ref_infer import load_bin, logits
from nuwaa.core.export_bin import export_state
from nuwaa.core.config import Config

ROOT = Path(__file__).resolve().parent.parent

class Stages(unittest.TestCase):
    def test_start_is_about_2m_and_grows(self):
        ps = [count_params(stage_config(n)) for n in ORDER]
        self.assertTrue(1_800_000 < ps[0] < 2_100_000); self.assertEqual(ps, sorted(ps))
        self.assertTrue(all(STAGES[n]["n_embd"] % STAGES[n]["n_head"] == 0 for n in ORDER))
    def test_phone_limit_blocks_big_stage(self):
        for n in ORDER[:-1]: self.assertEqual(phone_problems(stage_config(n)), [], n)
        with self.assertRaises(PhoneLimitError): check_phone_feasible(stage_config(ORDER[-1]))
        with self.assertRaises(ValueError): set_stage(ORDER[-1], tempfile.mkdtemp())
    def test_single_setting_selects_stage(self):
        d = tempfile.mkdtemp(); set_stage("s5m", d); self.assertEqual(selected_stage(d), "s5m")
    def test_bin_layout_and_numpy_reference(self):
        c = Config(2, 2, 16, 32); rng = np.random.default_rng(0)
        st = {n: (rng.standard_normal(s) * 0.1).astype("f4") for n, s in tensor_shapes(c)}
        f = tempfile.mktemp(suffix=".bin"); export_state(st, c, f)
        self.assertEqual(Path(f).stat().st_size, bin_size_bytes(c)); self.assertEqual(bin_size_bytes(c), HEADER_BYTES + 4 * count_params(c))
        c2, w = load_bin(f); lg = logits(c2, w, [257, 259, 70, 71]); self.assertEqual(lg.shape, (4, c.vocab)); self.assertTrue(np.isfinite(lg).all())
    def test_export_refuses_phone_breaking_stage(self):
        with self.assertRaises(PhoneLimitError): export_state({}, stage_config(ORDER[-1]), tempfile.mktemp())

def fake_report(root, stage, ok=True, total=0.5):
    (root / "stage_reports").mkdir(exist_ok=True); (root / "stage_artifacts" / stage).mkdir(parents=True, exist_ok=True)
    (root / "stage_artifacts" / stage / "model.bin").write_bytes(b"x")
    (root / "stage_reports" / f"{stage}.json").write_text(json.dumps({"all_ok": ok, "checks": {"a": ok}, "metrics": {"benchmark": {"total": total}}}))

class Gate(unittest.TestCase):
    def setUp(self): self.r = Path(tempfile.mkdtemp()); self.g = StageGate(str(self.r))
    def test_human_required(self):
        fake_report(self.r, "s2m")
        with self.assertRaises(PermissionError): self.g.accept("s2m", False)
    def test_cannot_skip_and_failed_checks_block(self):
        fake_report(self.r, "s5m"); self.assertFalse(self.g.accept("s5m", True)["accepted"])
        fake_report(self.r, "s2m", ok=False); self.assertFalse(self.g.accept("s2m", True)["accepted"]); self.assertIsNone(self.g.accepted())
    def test_bigger_must_be_stronger_else_rollback(self):
        fake_report(self.r, "s2m", total=0.3); self.assertTrue(self.g.accept("s2m", True)["accepted"])
        set_stage("s5m", str(self.r)); fake_report(self.r, "s5m", total=0.3)
        res = self.g.accept("s5m", True); self.assertFalse(res["accepted"]); self.assertEqual(selected_stage(str(self.r)), "s2m")
        fake_report(self.r, "s5m", total=0.4); self.assertTrue(self.g.accept("s5m", True)["accepted"]); self.assertEqual(self.g.accepted(), "s5m")
        self.assertEqual(self.g.rollback(), "s2m"); self.assertEqual(selected_stage(str(self.r)), "s2m")

class Bench(unittest.TestCase):
    def test_benchmark_scores_real_answers(self):
        items = load_items(str(ROOT / "data/eval")); self.assertGreaterEqual(len(items), 10)
        cats = {i["category"] for i in items}; self.assertEqual(cats, {"arabic", "chat", "code"})
        def good(q):
            for i in items:
                if i["user"] == q:
                    if "expect" in i: return i["expect"][0]
                    return {"ضربه في 7": "def solve(n): return n*7", "11": "def solve(n): return n+11", "فرديا": "def solve(n): return n%2==1",
                            "صغيرة": "def solve(s): return s.lower()", "ثلاثة": "```python\ndef solve(a,b,c): return a+b+c\n```"}[next(k for k in ["ضربه في 7","11","فرديا","صغيرة","ثلاثة"] if k in q)]
        self.assertEqual(run_benchmark(good, str(ROOT / "data/eval"))["total"], 1.0)
        self.assertEqual(run_benchmark(lambda q: "لا أعرف", str(ROOT / "data/eval"))["total"], 0.0)
    def test_no_eval_leakage_into_training(self):
        train = set()
        for f in (ROOT / "data").glob("*.jsonl"): train |= {json.loads(l)["user"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
        for i in load_items(str(ROOT / "data/eval")): self.assertNotIn(i["user"], train)

if __name__ == "__main__": unittest.main()
