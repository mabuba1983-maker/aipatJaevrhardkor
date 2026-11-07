"""One slow, careful improvement cycle (data + weights; code stays locked): button press -> retrain from scratch on all data
(including what the user taught it) -> every stage check -> compare to the accepted model -> accept only if strictly better AND you ticked approve.
python -m nuwaa.selfimprove.cycle --steps 3000 [--approve] [--stage s2m]"""
import argparse, json, time
from pathlib import Path
from .button import consume_press

def run_cycle(root=".", steps=3000, approve=False, stage=None):
    root = Path(root)
    consume_press(root / "self_improve_press.json")           # raises PermissionError unless a human pressed the button
    from ..core.stage_gate import StageGate                    # imported late: nothing heavy runs before the permission check
    from ..core.stages import selected_stage
    from ..core.run_stage import run_stage
    g = StageGate(str(root)); stage = stage or selected_stage(str(root))
    if not g.can_train(stage): return _log(root, {"stage": stage, "decision": "refused", "reasons": [f"not allowed now (accepted={g.accepted()}, next={g.next_allowed()})"]})
    rep = run_stage(stage, steps, root=str(root))
    if approve: res = g.accept(stage, True)
    else: res = {"accepted": False, "reasons": ["you did not tick approve: report only, nothing was changed"]}
    return _log(root, {"stage": stage, "all_ok": rep["all_ok"], "benchmark": rep["metrics"]["benchmark"], "decision": "accepted" if res["accepted"] else "kept previous", "reasons": res.get("reasons", [])})

def _log(root, rec):
    rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(Path(root) / "self_improve_log.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=2)); return rec

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--steps", type=int, default=3000); ap.add_argument("--approve", action="store_true"); ap.add_argument("--stage")
    a = ap.parse_args(); run_cycle(".", a.steps, a.approve, a.stage)
