# -*- coding: utf-8 -*-
"""Put the trained weights into nuwaa-ui.html (between /*ENGINE-START* and /*ENGINE-END*/):  python tools/build_ui.py [weights/nlm2.npz]
The page carries the weights as float16 (half the size); the engine in tools/ui_engine.js reads them. Run it again after every retraining."""
import base64, gzip, json, struct, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.lm.gru import GRULM

def blob(m):
    V = m.nv; ch = json.dumps(m.chars, ensure_ascii=False).encode("utf-8"); P = m.P
    out = [b"NLM2", struct.pack("<iii", m.E, m.H, V), struct.pack("<i", len(ch)), ch]
    for a in (P["E"][:V], P["Wx1"], P["Wh1"], P["b1"], P["Wx2"], P["Wh2"], P["b2"], P["Wo"][:, :V], P["bo"][:V]): out.append(np.ascontiguousarray(a, dtype="<f2").tobytes())
    return b"".join(out)

def main(w=None):
    m = GRULM.load(w or ROOT / "weights" / "nlm2.npz"); js = (ROOT / "tools" / "ui_engine.js").read_text(encoding="utf-8").replace("__WEIGHTS_B64__", base64.b64encode(blob(m)).decode("ascii"))
    p = ROOT / "nuwaa-ui.html"; h = p.read_text(encoding="utf-8"); a = h.index("/*ENGINE-START*"); b = h.index("/*ENGINE-END*/") + len("/*ENGINE-END*/")
    h = h[:a] + js.strip() + h[b:]
    def inject(h, start, end, body):
        a = h.index(start) + len(start); b = h.index(end); return h[:a] + "\n" + body.strip() + "\n" + h[b:]
    h = inject(h, "/*TRAINER-START*/", "/*TRAINER-END*/", (ROOT / "tools" / "ui_trainer.js").read_text(encoding="utf-8"))
    h = inject(h, "/*PAGE-START*/", "/*PAGE-END*/", (ROOT / "tools" / "ui_page.js").read_text(encoding="utf-8"))
    corpus = ROOT / "android" / "app" / "src" / "main" / "assets" / "train.txt"
    gz = base64.b64encode(gzip.compress(corpus.read_bytes(), 9)).decode("ascii") if corpus.exists() else ""
    h = inject(h, "/*CORPUS-START*/", "/*CORPUS-END*/", gz)
    p.write_text(h, encoding="utf-8"); print("nuwaa-ui.html:", p.stat().st_size, "bytes")

if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else None)
