"""Run candidate code in an isolated temp copy: separate process, timeout, CPU/memory limits, no network env."""
import os, shutil, subprocess, sys, tempfile
try:
    import resource
except ImportError:  # non-Unix
    resource = None

def _limits():
    if resource:
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 << 20, 10 << 20))

def run_in_sandbox(project_dir: str, cmd: list[str], timeout=120):
    tmp = tempfile.mkdtemp(prefix="nuwaa_sbx_")
    work = os.path.join(tmp, "work"); shutil.copytree(project_dir, work, ignore=shutil.ignore_patterns("versions", ".git", "__pycache__"))
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "NO_NETWORK": "1", "HOME": tmp}
    try:
        p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
                           preexec_fn=_limits if resource else None)
        return {"ok": p.returncode == 0, "code": p.returncode, "out": p.stdout[-4000:], "err": p.stderr[-4000:], "work": work}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "out": "", "err": "timeout", "work": work}
