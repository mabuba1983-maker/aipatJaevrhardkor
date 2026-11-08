"""python -m nuwaa.core.stage_cli plan | set <stage> | accept <stage> --human | rollback | apk <stage> <apk_path>"""
import json, sys
from pathlib import Path
from .stages import STAGES, ORDER, stage_config, set_stage, selected_stage
from .layout import count_params
from .limits import weights_mb, estimate_phone_ram_mb, phone_problems
from .stage_gate import StageGate

def main(argv):
    cmd = argv[0] if argv else "plan"; g = StageGate(".")
    if cmd == "plan":
        print(f"selected={selected_stage()} accepted={g.accepted()} next_allowed={g.next_allowed()}")
        for n in ORDER:
            c = stage_config(n); p = phone_problems(c)
            print(f"{n:14s} {count_params(c):>12,} params  {weights_mb(c):6.1f}MB  ramEst {estimate_phone_ram_mb(c):4.0f}MB  " + ("PHONE OK" if not p else "BLOCKED: " + "; ".join(p)))
    elif cmd == "set": set_stage(argv[1]); print("selected", argv[1])
    elif cmd == "accept": print(json.dumps(g.accept(argv[1], "--human" in argv), indent=2, ensure_ascii=False))
    elif cmd == "rollback": print("accepted now:", g.rollback())
    elif cmd == "apk":
        f = Path("stage_reports") / f"{argv[1]}.json"; r = json.loads(f.read_text())
        r["metrics"]["apk_total_mb"] = round(Path(argv[2]).stat().st_size / 1e6, 2); r["apk_built"] = True
        f.write_text(json.dumps(r, indent=2, ensure_ascii=False)); print("apk MB", r["metrics"]["apk_total_mb"])
    else: print(__doc__)
if __name__ == "__main__": main(sys.argv[1:])
