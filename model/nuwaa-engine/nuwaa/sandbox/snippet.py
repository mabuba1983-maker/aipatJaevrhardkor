"""Run one untrusted Python snippet (e.g. model-written code) in a throwaway dir: isolated process, timeout, CPU/RAM limits.
Returns the REAL stdout/stderr (including the real traceback on failure) so a caller can feed the actual
error back to the model. This is the only honest way to "self-correct": the model never sees its own output
unless something really executes it and reports back what happened.
"""
import os, subprocess, sys, tempfile
try:
    import resource
except ImportError:
    resource = None


def _limits(cpu_seconds=None, ram_bytes=None):
    if not resource:
        return
    if cpu_seconds:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    if ram_bytes:
        resource.setrlimit(resource.RLIMIT_AS, (ram_bytes, ram_bytes))
    # cpu_seconds=None / ram_bytes=None (the new default) = no cap at all, i.e. "unlimited" —
    # you're running this on your own machine, so it's your call; pass real numbers back in if you
    # want the old safety net (e.g. cpu_seconds=10, ram_bytes=512<<20).


def run_snippet(code: str, timeout=None, cpu_seconds=None, ram_bytes=None) -> dict:
    """timeout=None = no wall-clock cutoff either (slow-but-thorough, like you asked for).
    Returns {"ok": bool, "stdout": str, "stderr": str, "returncode": int|None, "timed_out": bool}."""
    d = tempfile.mkdtemp(prefix="nuwaa_snip_")
    path = os.path.join(d, "t.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    try:
        r = subprocess.run(
            [sys.executable, "-I", "t.py"], cwd=d,
            env={"PATH": os.environ.get("PATH", "")},
            capture_output=True, text=True, timeout=timeout,
            preexec_fn=(lambda: _limits(cpu_seconds, ram_bytes)) if resource else None,
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout[-200000:], "stderr": r.stderr[-200000:],
                "returncode": r.returncode, "timed_out": False}
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "stdout": (e.stdout or "")[-200000:], "stderr": (e.stderr or "") + "\n(timeout)",
                "returncode": None, "timed_out": True}
