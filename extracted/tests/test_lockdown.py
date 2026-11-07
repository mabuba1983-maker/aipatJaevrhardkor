# -*- coding: utf-8 -*-
"""The model can produce text (code it writes in a reply) and can be re-trained (its WEIGHTS change), but it can never touch its own behaviour:
the Python code, the Kotlin code, the safety gate, the sandbox, or the developer-file format. These tests guard that line so it cannot quietly move.
"""
import ast, re, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
AKT = ROOT / "android" / "app" / "src" / "main" / "java" / "ai" / "nuwaa"

def read(p): return p.read_text(encoding="utf-8")

class PythonSideNeverWritesSourceOrRuns(unittest.TestCase):
    """selfplay.py, pretrain_gru.py and studio.py are the only code that changes the model. None of them may write a .py/.kt/.js file into the
    repository itself (only into a throwaway temp directory to run a candidate snippet), and none may use exec/eval/compile on untrusted text."""
    FILES = ["nuwaa/lm/selfplay.py", "nuwaa/lm/pretrain_gru.py", "tools/studio.py", "tools/train_gru_torch.py"]
    def test_no_write_into_the_source_tree(self):
        for rel in self.FILES:
            src = read(ROOT / rel)
            # every write of a .py/.kt/.js file must target a tempfile path (mkdtemp / TemporaryDirectory), never a path under the repo
            for m in re.finditer(r'write_text\(|open\([^)]*["\']w', src):
                window = src[max(0, m.start() - 200):m.start() + 80]
                if re.search(r'\.(py|kt|js)["\']', window):
                    self.assertTrue(re.search(r'mkdtemp|TemporaryDirectory|tempfile', window), f"{rel}: writes a source-like file outside a temp sandbox near: {window!r}")
    def test_no_dynamic_execution_of_model_or_user_text(self):
        for rel in self.FILES:
            src = read(ROOT / rel)
            for bad in ("\neval(", " eval(", "exec(", "__import__("):
                self.assertNotIn(bad, src.replace("eval_loss", "").replace("evalLoss", ""), f"{rel} contains {bad!r}")
    def test_selfplay_sandbox_rejects_dangerous_code_before_running_it(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from nuwaa.lm import selfplay as sp
        for bad in ("import os\nprint(1)", "eval('1')", "open('/etc/passwd')", "__import__('os')", "exec('1')"):
            self.assertFalse(sp.static_ok(bad), bad)

class DeveloperFileCarriesNoCode(unittest.TestCase):
    """The format the model's self-development produces (the «developer file» / devfile) must only ever be weights + a memory log, verified by hash,
    and the checker must never execute anything it contains."""
    def test_devfile_format_has_no_code_entry_and_is_documented_as_such(self):
        src = read(ROOT / "nuwaa" / "lm" / "devfile.py")
        self.assertIn("It never carries code, and nothing in it is executed", src)
        self.assertNotIn("exec(", src); self.assertNotIn("eval(", src)
        import re as _re
        names = set(_re.findall(r'z\.writestr\("([^"]+)"', src))
        self.assertEqual(names, {"manifest.json", "nlm2.bin", "memory.txt"})   # exactly these three; nothing executable ever enters the zip
    def test_the_old_mind_gate_protects_its_own_safety_files(self):
        src = read(ROOT / "nuwaa" / "validator" / "validator.py")
        for must in ("nuwaa/validator", "nuwaa/selfimprove/button.py", "nuwaa/sandbox"): self.assertIn(must, src)
        self.assertIn("forbidden call", src)      # eval/exec/__import__ in a candidate file fails the gate

class AndroidNeverExecutesModelOutputOrLoadsCode(unittest.TestCase):
    """Nothing in the app may run code the model wrote, load a class dynamically, or shell out. Code the model writes for the user is saved as a
    file and shown with a warning to review it before using it — it is never executed by the app itself."""
    def test_no_execution_primitives_anywhere_in_the_app(self):
        banned = ("ProcessBuilder", "Runtime.getRuntime().exec(", "DexClassLoader", "PathClassLoader", "loadClass(", "javax.script", "WebView")
        for kt in AKT.glob("*.kt"):
            src = read(kt)
            for b in banned: self.assertNotIn(b, src, f"{kt.name} contains {b!r}")
    def test_file_tools_never_runs_code_it_writes(self):
        ft = read(AKT / "FileTools.kt"); m = read(AKT / "MainActivity.kt")
        self.assertIn("لم أشغّل الكود", m + ft + read(AKT / "Brain.kt"))   # the user is explicitly told the code was not executed
        for banned in ("ProcessBuilder", ".exec(", "Runtime.getRuntime()"): self.assertNotIn(banned, ft)

if __name__ == "__main__": unittest.main()
