import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import numpy as np
from nuwaa.lm.gru import GRULM
import scale_up

class Scale(unittest.TestCase):
    def test_widened_model_behaves_exactly_like_the_old_one(self):
        a = GRULM(16, 24, seed=3); a.encode("س:مرحبا\nج:أهلا بك.\n")
        b = a.widened(32, 80); ids = a.encode("س:مرحبا\nج:أهلا\n", grow=False)
        self.assertAlmostEqual(a.bpc(ids), b.bpc(ids), places=4); self.assertGreater(b.n_params(), a.n_params() * 3)
    def test_parameter_count_formula_matches_the_real_model(self):
        for E, H in ((16, 24), (64, 96), (128, 256)):
            self.assertEqual(scale_up.count(E, H), GRULM(E, H).n_params())
    def test_picks_a_hidden_size_for_a_target(self):
        for target in (10_000_000, 100_000_000):
            H = scale_up.pick_hidden(target, 128)
            self.assertLessEqual(scale_up.count(128, H), target); self.assertGreater(scale_up.count(128, H + 32), target)
    def test_torch_trainer_is_valid_python_and_checks_itself(self):
        src = (Path(__file__).resolve().parent.parent / "tools" / "train_gru_torch.py").read_text(encoding="utf-8")
        compile(src, "train_gru_torch.py", "exec"); self.assertIn("STOP: the torch network does not match", src)

class Hardware(unittest.TestCase):
    def test_report_and_advice(self):
        from nuwaa.lm import hw
        r = hw.report(); self.assertIn("المعالج", r); self.assertIn("التوصية", r)
        self.assertIn("100 مليون", hw.advice({"gpus": [("X", 16.0, "t")]})); self.assertIn("40 مليون", hw.advice({"gpus": [("X", 8.0, "t")]}))
        self.assertIn("كرت", hw.advice({"gpus": []}))
    def test_colab_notebook_is_valid(self):
        import json
        nb = json.load(open(Path(__file__).resolve().parent.parent / "tools" / "Nuwaa_40m_colab.ipynb", encoding="utf-8"))
        src = "".join("".join(c["source"]) for c in nb["cells"]); self.assertIn("--target 40000000", src); self.assertIn("train_gru_torch.py", src)

if __name__ == "__main__": unittest.main()
