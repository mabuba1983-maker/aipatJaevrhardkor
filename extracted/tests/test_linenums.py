# -*- coding: utf-8 -*-
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.skills.linenums import strip_line_numbers, _NOT_CODE_START
KT = ROOT / "android/app/src/main/java/ai/nuwaa"

class LineNums(unittest.TestCase):
    def test_shared_cases(self):
        for c in json.loads((ROOT / "data/linenums_cases.json").read_text(encoding="utf-8")):
            self.assertEqual(strip_line_numbers(c["in"]), (c["out"], c["n"]), c["in"])
    def test_real_code_is_never_damaged(self):
        for t in ["print(1)\nprint(2)", "x = 3\n4 * x", "1 + 2", "def f():\n    return 1\n", ""]:
            self.assertEqual(strip_line_numbers(t), (t, 0))
    def test_kotlin_mirror_and_button_exist(self):
        k = (KT / "LineNumbers.kt").read_text(encoding="utf-8"); m = (KT / "MainActivity.kt").read_text(encoding="utf-8")
        self.assertIn(f'NOT_CODE = "{_NOT_CODE_START}"', k)
        self.assertIn("LineNumbers.strip(", m); self.assertIn("إزالة الأرقام الجانبية", m); self.assertIn("private fun stripNumbers()", m)
        for part in ("0.8 * nonempty", "0.5 * steps", "code < 2"): self.assertIn(part, k)
if __name__ == "__main__": unittest.main()
