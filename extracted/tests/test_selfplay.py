import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.lm import selfplay as sp

F = "```"
def ans(code, shown): return "هذا الكود:\n" + F + "python\n" + code + "\n" + F + "\nالناتج: " + shown

class Verifier(unittest.TestCase):
    def test_right_answer_is_proven(self):
        ok, code = sp.verify(ans("print(sum([1, 2, 3]))", "6"), "6\n"); self.assertTrue(ok); self.assertIn("sum", code)
    def test_wrong_output_is_not(self):
        self.assertFalse(sp.verify(ans("print(sum([1, 2, 3]))", "6"), "7\n")[0])
    def test_claimed_output_is_checked_only_when_strict(self):
        t = ans("print(1 + 1)", "3")
        self.assertTrue(sp.verify(t, "2\n")[0]); self.assertFalse(sp.verify(t, "2\n", strict=True)[0])
    def test_a_wrong_claim_is_replaced_by_the_real_output(self):
        fixed = sp.with_true_output(ans("print(1 + 1)", "3"), "2\n")
        self.assertTrue(fixed.endswith("الناتج: 2")); self.assertTrue(sp.verify(fixed, "2\n", strict=True)[0])
    def test_code_that_crashes_is_not(self):
        self.assertFalse(sp.verify(ans("print(1 / 0)", "1"), "1\n")[0])
    def test_dangerous_code_never_runs(self):
        for bad in ("import os\nprint(1)", "print(open('/etc/passwd').read())", "print(eval('1'))", "print(().__class__)", "import subprocess\nprint(1)"):
            self.assertFalse(sp.static_ok(bad), bad)
    def test_no_code_block(self):
        self.assertFalse(sp.verify("مرحبا", "1\n")[0])

class Gate(unittest.TestCase):
    def test_a_real_round_needs_a_button_press(self):
        d = tempfile.mkdtemp()
        with self.assertRaises(PermissionError): sp.main(["--press", str(Path(d) / "none.json"), "--tasks", "1"])
    def test_generation_has_memory_off(self):
        seen = {}
        class Stub:
            def __init__(self, lm, seed=0): pass
            def reply(self, q, **kw): seen.update(kw); return ("x", [])
        old = sp.Session; sp.Session = Stub
        try: sp.generate(None, "q", 1, 0.6)
        finally: sp.Session = old
        self.assertEqual(seen["mem_gain"], 0.0); self.assertEqual(seen["short_gain"], 0.0)
    def test_fresh_tasks_are_new_and_reference_runs(self):
        t = sp.fresh_tasks(5, 6, set()); self.assertEqual(len(t), 6)
        for q, ref in t: self.assertTrue(ref.strip())

if __name__ == "__main__": unittest.main()
