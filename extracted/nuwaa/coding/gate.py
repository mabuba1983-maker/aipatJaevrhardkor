"""Coding permission gate. Locked by default. Unlocks in stages only after required tests pass."""
import json
from pathlib import Path
LEVELS = ["locked", "read_only", "propose_in_sandbox"]  # there is NO level that edits the base directly
class CodingGate:
    def __init__(self, path="coding_state.json"):
        self.p = Path(path)
        if not self.p.exists(): self.p.write_text(json.dumps({"level": "locked"}))
    def level(self): return json.loads(self.p.read_text())["level"]
    def unlock_next(self, tests_passed: bool, approved_by_human: bool):
        if not (tests_passed and approved_by_human): raise PermissionError("need passing tests AND human approval")
        i = LEVELS.index(self.level())
        if i + 1 >= len(LEVELS): raise PermissionError("already at highest level")
        self.p.write_text(json.dumps({"level": LEVELS[i + 1]})); return LEVELS[i + 1]
    def require(self, needed: str):
        if LEVELS.index(self.level()) < LEVELS.index(needed): raise PermissionError(f"coding is '{self.level()}', needs '{needed}'")
