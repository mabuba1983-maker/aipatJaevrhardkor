import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import prepare_corpus as pc
HAVE_NODE = shutil.which("node") is not None

class Corpus(unittest.TestCase):
    def test_only_programming_and_arabic_survive(self):
        d = tempfile.mkdtemp(); (Path(d) / "a.py").write_text("def add(a, b):\n    \"\"\"جمع رقمين\"\"\"\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n" * 3, encoding="utf-8")
        (Path(d) / "b.txt").write_text("الصبر مفتاح الفرج. العلم نور يهدي صاحبه إلى الطريق المستقيم. " * 4, encoding="utf-8")
        (Path(d) / "c.txt").write_text("这是一个中文文档，包含很多中文字符，不应该进入训练数据。" * 6, encoding="utf-8")
        (Path(d) / "p.jsonl").write_text(json.dumps({"instruction": "اكتب دالة تجمع رقمين", "output": "def add(a, b):\n    return a + b"}, ensure_ascii=False) + "\n", encoding="utf-8")
        out = str(Path(d) / "out.txt"); pc.main(["--src", d, "--out", out])
        lines = open(out, encoding="utf-8").read().splitlines(); text = "".join(lines)
        self.assertTrue(lines); self.assertFalse(any(ord(c) > 0x652 and c not in pc.ALLOWED for c in text))
        self.assertNotIn("中", text)
        self.assertTrue(any(l.startswith("س:") and "\tج:" in l for l in lines)); self.assertTrue(all(len(l) <= pc.MAXC + 10 or l.startswith("س:") for l in lines))
        self.assertEqual(len(lines), len(set(lines)))

@unittest.skipUnless(HAVE_NODE, "node is not installed")
class Trainer(unittest.TestCase):
    def test_gradients_loss_and_learning(self):
        """The web trainer's loss equals numpy's on the same model, its gradients match finite differences, and training lowers the loss."""
        import numpy as np
        from nuwaa.lm.gru import GRULM
        m = GRULM(8, 16, seed=5); m.encode("س:مرحبا\nج:أهلا بك\n"); V = m.nv; ids = m.encode("س:مرحبا\nج:أهلا بك\n", grow=False)
        P = {k: v.astype(np.float64) for k, v in m.P.items()}; H = 16
        sig = lambda x: 1 / (1 + np.exp(-x))
        def cell(gx, h, Wh):
            rz = sig(gx[:2 * H] + h @ Wh[:, :2 * H]); r, z = rz[:H], rz[H:]; n = np.tanh(gx[2 * H:] + (r * h) @ Wh[:, 2 * H:]); return (1 - z) * h + z * n
        h1 = np.zeros(H); h2 = np.zeros(H); tot = 0.0
        for i in range(len(ids) - 1):
            h1 = cell(P["E"][ids[i]] @ P["Wx1"] + P["b1"], h1, P["Wh1"]); h2 = cell(h1 @ P["Wx2"] + P["b2"], h2, P["Wh2"])
            lg = (h2 @ P["Wo"] + P["bo"])[:V]; lg -= lg.max(); p = np.exp(lg) / np.exp(lg).sum(); tot += -np.log(p[ids[i + 1]])
        ref = {"E": 8, "H": 16, "V": V, "ids": [int(x) for x in ids], "loss": tot / (len(ids) - 1),
               "P": {"PE": P["E"][:V].ravel().tolist(), "Wx1": P["Wx1"].ravel().tolist(), "Wh1": P["Wh1"].ravel().tolist(), "b1": P["b1"].tolist(), "Wx2": P["Wx2"].ravel().tolist(),
                     "Wh2": P["Wh2"].ravel().tolist(), "b2": P["b2"].tolist(), "Wo": P["Wo"][:, :V].ravel().tolist(), "bo": P["bo"][:V].tolist()}}
        d = tempfile.mkdtemp(); json.dump(ref, open(os.path.join(d, "ref.json"), "w"))
        js = ("const {makeTrainer}=require(%r);const ref=JSON.parse(require('fs').readFileSync(%r,'utf8'));"
              "const D={E:ref.E,H:ref.H,V:ref.V};const P={};for(const k in ref.P)P[k]=Float64Array.from(ref.P[k]);const T=makeTrainer(P,D,Float64Array);"
              "const l=T.lossAndGrad(ref.ids);let worst=0;"
              "for(const k of T.names){const g=T.grads[k].slice();for(let c=0;c<25;c++){const i=Math.floor(Math.random()*P[k].length),e=1e-6,o=P[k][i];P[k][i]=o+e;const a=T.evalLoss(ref.ids);P[k][i]=o-e;const b=T.evalLoss(ref.ids);P[k][i]=o;"
              "const num=(a-b)/(2*e),ana=g[i];if(Math.abs(num)+Math.abs(ana)>2e-4)worst=Math.max(worst,Math.abs(num-ana)/(Math.abs(num)+Math.abs(ana)))}}"
              "const before=T.evalLoss(ref.ids);for(let s=0;s<60;s++){T.lossAndGrad(ref.ids);T.adam(0.02)}"
              "console.log(JSON.stringify({loss:l,ref:ref.loss,worst,before,after:T.evalLoss(ref.ids)}))") % (str(ROOT / "tools" / "ui_trainer.js"), os.path.join(d, "ref.json"))
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=120); self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertAlmostEqual(o["loss"], o["ref"], places=5); self.assertLess(o["worst"], 1e-4); self.assertLess(o["after"], o["before"] * 0.7)

    def test_zip_writer_makes_a_valid_zip(self):
        import zipfile
        src = (ROOT / "tools" / "ui_page.js").read_text(encoding="utf-8"); a = src.index("/*ZIP-START*/"); b = src.index("/*ZIP-END*/")
        d = tempfile.mkdtemp(); out = os.path.join(d, "t.zip")
        js = src[a:b] + "(async()=>{const z=makeZip([{name:'proj/main.py',body:'print(\"مرحبا\")\\n'},{name:'proj/data.csv',body:'a,b\\n1,2\\n'}]);require('fs').writeFileSync(%r,Buffer.from(await z.arrayBuffer()))})()" % out
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30); self.assertEqual(r.returncode, 0, r.stderr)
        with zipfile.ZipFile(out) as z:
            self.assertIsNone(z.testzip()); self.assertEqual(sorted(z.namelist()), ["proj/data.csv", "proj/main.py"]); self.assertIn("مرحبا", z.read("proj/main.py").decode("utf-8"))

    def test_page_has_the_buttons_and_no_prewritten_bot_bubble(self):
        h = (ROOT / "nuwaa-ui.html").read_text(encoding="utf-8")
        for k in ('id="fbtn"', 'id="mbar"', 'id="t3"', 'id="tgo"', 'id="pct"', "function makeZip", "respondFile", "makeTrainer"): self.assertIn(k, h)
        self.assertNotIn("add('أهلا! أنا نواة", h)               # the welcome line is an interface notice, not a bot reply

if __name__ == "__main__": unittest.main()
