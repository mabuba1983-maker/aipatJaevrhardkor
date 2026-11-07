"""Run one untrusted Python snippet (e.g. model-written code) in a throwaway dir: isolated mode, timeout, CPU/RAM limits."""
import os, subprocess, sys, tempfile
try: import resource
except ImportError: resource = None
def _limits():
    if resource:
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10)); resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
def run_snippet(code: str, timeout=10) -> bool:
    d = tempfile.mkdtemp(prefix="nuwaa_snip_")
    with open(os.path.join(d, "t.py"), "w", encoding="utf-8") as f: f.write(code)
    try:
        r = subprocess.run([sys.executable, "-I", "t.py"], cwd=d, env={"PATH": os.environ.get("PATH", "")}, capture_output=True,
                           timeout=timeout, preexec_fn=_limits if resource else None)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
