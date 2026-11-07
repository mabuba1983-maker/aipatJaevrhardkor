import sys, tempfile, unittest, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.validator.validator import static_gate

class V(unittest.TestCase):
    def _pair(self):
        d = Path(tempfile.mkdtemp()); (d/"b/nuwaa/validator").mkdir(parents=True); (d/"c/nuwaa/validator").mkdir(parents=True)
        return d/"b", d/"c"
    def test_rejects_protected_and_forbidden(self):
        b, c = self._pair()
        (b/"nuwaa/validator/validator.py").write_text("x=1"); (c/"nuwaa/validator/validator.py").write_text("x=2")
        (c/"nuwaa/evil.py").write_text("import socket\neval('1')")
        _, problems = static_gate(b, c); t = " ".join(problems)
        self.assertIn("protected", t); self.assertIn("forbidden import socket", t); self.assertIn("forbidden call eval", t)
    def test_rejects_syntax_error(self):
        b, c = self._pair(); (c/"nuwaa/a.py").write_text("def (:")
        self.assertTrue(any("syntax" in p for p in static_gate(b, c)[1]))
    def test_accepts_clean_small_change(self):
        b, c = self._pair(); (c/"nuwaa/a.py").write_text("def f():\n    return 1\n")
        self.assertEqual(static_gate(b, c)[1], [])
if __name__ == "__main__": unittest.main()
