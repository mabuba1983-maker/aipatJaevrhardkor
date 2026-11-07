"""A capability is 'installed' ONLY if its verification test really passes. The model cannot just claim it."""
import importlib, json
from pathlib import Path
class Capabilities:
    def __init__(self, path="capabilities.json"):
        self.p = Path(path)
        if not self.p.exists(): self.p.write_text(json.dumps({}))
    def state(self): return json.loads(self.p.read_text())
    def verify(self, name: str, module: str, check_fn: str = "self_check") -> bool:
        ok = False
        try: ok = bool(getattr(importlib.import_module(module), check_fn)())
        except Exception: ok = False
        s = self.state(); s[name] = {"verified": ok, "module": module}; self.p.write_text(json.dumps(s, indent=2)); return ok
    def has(self, name): return self.state().get(name, {}).get("verified", False)
    def report(self, name):
        return f"capability '{name}': " + ("VERIFIED and working" if self.has(name) else "NOT installed or failed verification")
