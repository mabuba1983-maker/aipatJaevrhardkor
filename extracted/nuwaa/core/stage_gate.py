"""Stage gate: a bigger stage is only allowed after the previous one passed ALL checks, is accepted by a human, and
(for every stage after the first) scores strictly higher on the real benchmark. Otherwise the previous size stays."""
import json, shutil
from pathlib import Path
from .stages import ORDER, stage_config, set_stage
from .limits import phone_problems
from ..versioning.store import VersionStore

class StageGate:
    def __init__(self, root="."):
        self.root = Path(root); self.sf = self.root / "stage_state.json"
        if not self.sf.exists(): self.sf.write_text(json.dumps({"accepted": None, "history": []}))
        self.vs = VersionStore(self.root / "stage_versions")
    def _s(self): return json.loads(self.sf.read_text())
    def report(self, stage):
        f = self.root / "stage_reports" / f"{stage}.json"
        return json.loads(f.read_text()) if f.exists() else None
    def accepted(self): return self._s()["accepted"]
    def accepted_report(self):
        f = self.root / "stage_reports" / "accepted_report.json"
        return json.loads(f.read_text()) if f.exists() else None
    def _publish(self, stage, report):
        (self.root / "stage_reports").mkdir(exist_ok=True)
        f = self.root / "stage_reports" / "accepted_report.json"
        if report is None:
            if f.exists(): f.unlink()
        else: f.write_text(json.dumps(report, ensure_ascii=False))
        b = self.root / "stage_artifacts" / (stage or "") / "model.bin"
        if stage and b.exists(): (self.root / "model_accepted").mkdir(exist_ok=True); shutil.copy(b, self.root / "model_accepted" / "model.bin")
    def next_allowed(self):
        a = self.accepted()
        if a is None: return ORDER[0]
        i = ORDER.index(a) + 1
        return ORDER[i] if i < len(ORDER) else None
    def can_train(self, stage): return stage in (self.next_allowed(), self.accepted())
    def _reject(self, reasons):
        a = self.accepted()
        if a: set_stage(a, str(self.root))      # automatic rollback to the previous (accepted) size
        return {"accepted": False, "reasons": reasons, "selected_now": a}
    def accept(self, stage, human_ok):
        if not human_ok: raise PermissionError("a human must approve a stage")
        r = self.report(stage); why = []
        if stage not in (self.next_allowed(), self.accepted()): why.append(f"cannot skip stages (next allowed: {self.next_allowed()})")
        if not r: why.append("no report: run run_stage first")
        elif not r["all_ok"]: why.append("failed checks: " + ", ".join(k for k, v in r["checks"].items() if not v))
        pp = phone_problems(stage_config(stage)) if stage in ORDER else ["unknown stage"]
        if pp: why.append("not practical on a phone: " + "; ".join(pp))
        prev = self.accepted()
        if r and prev:
            pr = self.accepted_report()
            if not pr or r["metrics"]["benchmark"]["total"] <= pr["metrics"]["benchmark"]["total"]:
                why.append(f"not stronger than the accepted model ({prev}) on the real benchmark ({r['metrics']['benchmark']['total']} vs {pr['metrics']['benchmark']['total'] if pr else '?'}); more parameters alone do not count")
        if why: return self._reject(why)
        art = self.root / "stage_artifacts" / stage
        vid = self.vs.snapshot(str(art), f"stage {stage}", "human")
        s = self._s(); s["history"].append({"stage": stage, "version": vid, "report": r}); s["accepted"] = stage; self.sf.write_text(json.dumps(s))
        self._publish(stage, r); set_stage(stage, str(self.root)); return {"accepted": True, "version": vid, "selected_now": stage}
    def rollback(self):
        s = self._s()
        if not s["history"]: raise RuntimeError("nothing to roll back")
        s["history"].pop(); prev = s["history"][-1] if s["history"] else None
        s["accepted"] = prev["stage"] if prev else None; self.sf.write_text(json.dumps(s))
        if prev: self.vs.rollback(prev["version"], str(self.root / "stage_artifacts" / prev["stage"]))
        self._publish(prev["stage"] if prev else None, prev["report"] if prev else None)
        set_stage(prev["stage"] if prev else ORDER[0], str(self.root)); return s["accepted"]
