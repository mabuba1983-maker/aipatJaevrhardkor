# -*- coding: utf-8 -*-
"""Server improvement loop. YOU start it (by hand or from cron): that is the human decision. It never starts by itself.
  python server/improve.py --stage s5m --steps 20000            -> train, test, report only (nothing changes)
  python server/improve.py --stage s5m --steps 20000 --approve  -> if every check passes AND the real benchmark is strictly higher than the
                                                                   accepted model, the new model replaces the served one (the server reloads it by itself)
Steps: clean the data the server collected -> retrain FROM SCRATCH on all data -> all checks -> compare with the accepted model -> swap or keep.
What it improves: weights and data. It does NOT rewrite its own code."""
import argparse, os, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.learning.ingest import sanitize_lines
from nuwaa.selfimprove.button import record_press
from nuwaa.selfimprove import cycle

def clean_feedback(root):
    f = Path(root) / "data" / "user_feedback.jsonl"
    if not f.exists(): return 0
    lines = sanitize_lines(f.read_text(encoding="utf-8"), max_lines=10 ** 7)      # default keeps only the last 2000: far too few for a server
    tmp = f.with_suffix(".tmp"); tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"); os.replace(tmp, f)
    return len(lines)

def improve(root=ROOT, stage=None, steps=20000, approve=False, serve_model=None):
    root = Path(root); serve = Path(serve_model or os.environ.get("NUWAA_MODEL") or root / "model.pt")
    n = clean_feedback(root)
    record_press(root / "self_improve_press.json", "server")                          # the single-use, expiring permission the cycle requires
    rec = cycle.run_cycle(str(root), steps, approve, stage)
    rec["feedback_pairs"] = n
    if rec.get("decision") == "accepted":
        src = root / "stage_artifacts" / rec["stage"] / "model.pt"
        if not src.exists(): rec["decision"] = "accepted but model.pt missing: server model NOT changed"; return rec
        serve.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(serve.parent), suffix=".pt"); os.close(fd); shutil.copyfile(src, tmp); os.replace(tmp, serve)   # atomic swap
        rec["served_model"] = str(serve)
    return rec

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage"); ap.add_argument("--steps", type=int, default=20000); ap.add_argument("--approve", action="store_true")
    a = ap.parse_args(); improve(ROOT, a.stage, a.steps, a.approve)
