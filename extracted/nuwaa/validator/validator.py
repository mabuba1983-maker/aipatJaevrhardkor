"""Independent validator. It shares no code path with the proposer: it only sees the candidate directory.
A change is accepted ONLY if every gate passes. Any doubt = reject."""
import ast, json, sys
from pathlib import Path
from ..sandbox.runner import run_in_sandbox

FORBIDDEN_IMPORTS = {"socket", "requests", "urllib", "http", "ftplib", "smtplib", "ctypes", "subprocess", "shutil"}
PROTECTED = {"nuwaa/validator", "nuwaa/versioning", "nuwaa/coding/gate.py", "nuwaa/sandbox",
             "nuwaa/selfimprove/button.py", "nuwaa/selfimprove/cycle.py", "nuwaa/core/stage_gate.py",
             "nuwaa/mind/develop.py", "nuwaa/mind/verify.py", "nuwaa/mind/curriculum.py"}    # the mind cannot edit its own gate, verifier or teacher
MAX_CHANGED_FILES = 3  # gradual evolution: small steps only

def changed_files(base: Path, cand: Path):
    out = []
    for f in cand.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts and "versions" not in f.parts:
            r = f.relative_to(cand); b = base / r
            if not b.exists() or b.read_bytes() != f.read_bytes(): out.append(r.as_posix())
    return out

def static_gate(base: Path, cand: Path):
    ch = changed_files(base, cand); problems = []
    if not ch: problems.append("no changes")
    if len(ch) > MAX_CHANGED_FILES: problems.append(f"too many files changed ({len(ch)}>{MAX_CHANGED_FILES})")
    for r in ch:
        if any(r == p or r.startswith(p + "/") for p in PROTECTED): problems.append(f"protected path touched: {r}")
        if r.endswith(".py"):
            try: tree = ast.parse((cand / r).read_text(encoding="utf-8"))
            except SyntaxError as e: problems.append(f"syntax error in {r}: {e}"); continue
            for n in ast.walk(tree):
                mods = [a.name.split(".")[0] for a in n.names] if isinstance(n, ast.Import) else \
                       [(n.module or "").split(".")[0]] if isinstance(n, ast.ImportFrom) else []
                for m in mods:
                    if m in FORBIDDEN_IMPORTS: problems.append(f"forbidden import {m} in {r}")
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") in {"eval", "exec", "__import__"}:
                    problems.append(f"forbidden call {n.func.id} in {r}")
    return ch, problems

def score(project: str):
    """Run the benchmark suite in the sandbox. Returns (passed, total) or None on failure."""
    r = run_in_sandbox(project, [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], timeout=300)
    if not r["ok"] and "FAILED" not in r["err"] and "OK" not in r["err"]: return None, r
    import re
    m = re.search(r"Ran (\d+) test", r["err"]); n = int(m.group(1)) if m else 0
    f = re.search(r"failures=(\d+)", r["err"]); e = re.search(r"errors=(\d+)", r["err"])
    bad = (int(f.group(1)) if f else 0) + (int(e.group(1)) if e else 0)
    return (n - bad, n), r

def validate(base_dir: str, cand_dir: str):
    base, cand = Path(base_dir), Path(cand_dir)
    report = {"accepted": False, "reasons": []}
    ch, problems = static_gate(base, cand); report["changed"] = ch
    if problems: report["reasons"] = problems; return report
    b, _ = score(base_dir); c, rc = score(cand_dir)
    report["base_score"], report["cand_score"] = b, c
    if c is None or b is None: report["reasons"].append("could not run tests"); return report
    if c[0] != c[1]: report["reasons"].append("candidate fails some tests"); return report
    if c[1] < b[1]: report["reasons"].append("candidate removed tests"); return report
    if c[1] == b[1]: report["reasons"].append("no new test proves an improvement"); return report
    report["accepted"] = True; report["reasons"].append("all gates passed; awaiting human approval to promote")
    return report

if __name__ == "__main__":
    print(json.dumps(validate(sys.argv[1], sys.argv[2]), indent=2, ensure_ascii=False))
