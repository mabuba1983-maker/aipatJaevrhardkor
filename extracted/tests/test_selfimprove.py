import json, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.selfimprove.button import record_press, consume_press
from nuwaa.selfimprove.cycle import run_cycle
from nuwaa.learning.ingest import sanitize_lines
from nuwaa.skills.calc import try_math
from nuwaa.core.train import make_xy, load_examples
from nuwaa.core.stage_gate import StageGate
from nuwaa.core.stages import set_stage, selected_stage
from nuwaa.validator.validator import PROTECTED
ROOT = Path(__file__).resolve().parent.parent

class Button(unittest.TestCase):
    def test_no_press_no_improvement(self):
        d = tempfile.mkdtemp()
        with self.assertRaises(PermissionError): run_cycle(d, steps=1)
    def test_press_is_single_use_and_expires(self):
        f = Path(tempfile.mkdtemp()) / "p.json"; record_press(f); consume_press(f)
        with self.assertRaises(PermissionError): consume_press(f)
        record_press(f, now=time.time() - 7200)
        with self.assertRaises(PermissionError): consume_press(f)
    def test_button_files_are_protected_from_the_model(self):
        for p in ["nuwaa/selfimprove/button.py", "nuwaa/selfimprove/cycle.py", "nuwaa/core/stage_gate.py"]: self.assertIn(p, PROTECTED)

class Ingest(unittest.TestCase):
    def test_sanitize(self):
        good = json.dumps({"user": "س", "bot": "ج"}, ensure_ascii=False)
        txt = "\n".join([good, good, "not json", json.dumps({"user": "a"}), json.dumps({"user": "x" * 3000, "bot": "y"}), json.dumps({"user": "a\x00", "bot": "b"})])
        self.assertEqual(len(sanitize_lines(txt)), 1)

class Skills(unittest.TestCase):
    def test_shared_cases(self):
        for q, e in json.loads((ROOT / "data/skills_cases.json").read_text(encoding="utf-8")): self.assertEqual(try_math(q), e, q)
    def test_no_code_execution(self):
        for q in ["__import__('os')", "2 ** 9999999", "9" * 400 + " * " + "9" * 400 + " ^ 99"]: self.assertNotIn("Error", str(try_math(q)))

class Training(unittest.TestCase):
    def test_loss_only_on_answer(self):
        ex = load_examples(str(ROOT / "data")); self.assertGreater(len(ex), 300)
        x, y = make_xy(([257, 259, 10, 11, 260, 20, 21, 258], 5), 16)
        self.assertEqual([t for t in y if t != -100], [20, 21, 258]); self.assertEqual(len(x), len(y))

class Refresh(unittest.TestCase):
    def test_same_stage_refresh_needs_strictly_better(self):
        r = Path(tempfile.mkdtemp()); g = StageGate(str(r))
        def rep(total):
            (r / "stage_reports").mkdir(exist_ok=True); (r / "stage_artifacts/s2m").mkdir(parents=True, exist_ok=True); (r / "stage_artifacts/s2m/model.bin").write_bytes(b"x")
            (r / "stage_reports/s2m.json").write_text(json.dumps({"all_ok": True, "checks": {"a": True}, "metrics": {"benchmark": {"total": total}}}))
        rep(0.3); self.assertTrue(g.accept("s2m", True)["accepted"])
        rep(0.3); self.assertFalse(g.accept("s2m", True)["accepted"])
        rep(0.5); self.assertTrue(g.accept("s2m", True)["accepted"]); self.assertEqual(g.accepted_report()["metrics"]["benchmark"]["total"], 0.5)
        self.assertTrue((r / "model_accepted/model.bin").exists())
        g.rollback(); self.assertEqual(g.accepted_report()["metrics"]["benchmark"]["total"], 0.3)
if __name__ == "__main__": unittest.main()
