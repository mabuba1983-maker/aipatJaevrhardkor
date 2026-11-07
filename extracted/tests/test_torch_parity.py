import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try: import torch; HAS = True
except ImportError: HAS = False

@unittest.skipUnless(HAS, "PyTorch not installed (runs in CI)")
class P(unittest.TestCase):
    def test_param_count_save_reload_and_phone_parity(self):
        import numpy as np
        from nuwaa.core.config import Config
        from nuwaa.core.model import GPT
        from nuwaa.core.layout import count_params
        from nuwaa.core.export_bin import export_state
        from nuwaa.core.ref_infer import load_bin, logits
        for name in ["s2m", "s5m"]:
            from nuwaa.core.stages import stage_config
            cfg = stage_config(name); m = GPT(cfg).eval()
            self.assertEqual(sum(p.numel() for p in m.parameters()), count_params(cfg))
        cfg = Config(2, 2, 32, 64); m = GPT(cfg).eval(); f = tempfile.mktemp(suffix=".bin"); export_state(m.state_dict(), cfg, f)
        c2, w = load_bin(f); ids = [257, 259, 100, 101, 102, 260]
        ref = logits(c2, w, ids); real = m(torch.tensor([ids]))[0][0].detach().numpy()
        self.assertLess(float(np.abs(ref - real).max()), 1e-3)
        pt = tempfile.mktemp(suffix=".pt"); torch.save({"cfg": cfg.to_dict(), "state": m.state_dict()}, pt)
        m2 = GPT(cfg).eval(); m2.load_state_dict(torch.load(pt)["state"]); self.assertTrue(torch.equal(m(torch.tensor([ids]))[0], m2(torch.tensor([ids]))[0]))
    def test_training_reduces_loss(self):
        from nuwaa.core.train import train
        r = train("s2m", steps=60, bs=4, out=tempfile.mktemp(suffix=".pt"), data_dir=str(Path(__file__).resolve().parent.parent / "data"), log=lambda *_: None)
        self.assertTrue(r["finite"] and r["loss_last"] < r["loss_first"])
if __name__ == "__main__": unittest.main()
