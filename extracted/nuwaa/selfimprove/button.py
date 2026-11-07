"""The ONLY way self-improvement can start is a human pressing the button in the app (which starts the CI workflow).
A press is a single-use token that expires. Nothing in the model/pipeline creates presses on its own."""
import json, secrets, sys, time
from pathlib import Path
MAX_AGE_S = 3600

def record_press(path, source="app", now=None):
    Path(path).write_text(json.dumps({"t": time.time() if now is None else now, "nonce": secrets.token_hex(8), "source": source}))

def consume_press(path, now=None, max_age_s=MAX_AGE_S):
    p = Path(path)
    if not p.exists(): raise PermissionError("self-improvement is OFF: no button press")
    d = json.loads(p.read_text()); p.unlink()                         # single use
    if (time.time() if now is None else now) - d["t"] > max_age_s: raise PermissionError("button press expired")
    return d

if __name__ == "__main__":
    if sys.argv[1:2] == ["press"]: record_press("self_improve_press.json", sys.argv[2] if len(sys.argv) > 2 else "app"); print("press recorded")
