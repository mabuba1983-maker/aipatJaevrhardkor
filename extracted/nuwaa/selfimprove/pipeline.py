"""Slow, careful pipeline: problem -> proposal -> candidate copy -> tests -> independent validation -> compare -> human approval -> new version.
The pipeline never writes to the base directory by itself."""
import shutil, tempfile
from pathlib import Path
from ..coding.gate import CodingGate
from ..validator.validator import validate
from ..versioning.store import VersionStore

class SelfImprove:
    def __init__(self, base="."):
        self.base = Path(base); self.gate = CodingGate(self.base / "coding_state.json"); self.vs = VersionStore(self.base / "versions")
    def make_candidate(self):
        self.gate.require("propose_in_sandbox")
        d = Path(tempfile.mkdtemp(prefix="nuwaa_cand_"))
        shutil.copytree(self.base, d / "cand", ignore=shutil.ignore_patterns("versions", ".git", "__pycache__", "*.pt", "*.bin"))
        return d / "cand"   # proposer edits files ONLY here
    def evaluate(self, cand: Path):
        return validate(str(self.base), str(cand))
    def promote(self, cand: Path, note: str, human_ok: bool):
        rep = self.evaluate(cand)
        if not rep["accepted"]: return {"promoted": False, "report": rep}
        if not human_ok: return {"promoted": False, "report": rep, "waiting": "human approval"}
        vid = self.vs.snapshot(str(cand), note, "validator+human")
        return {"promoted": True, "version": vid, "report": rep}
