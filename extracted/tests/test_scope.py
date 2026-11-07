import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.skills import scope

class Scope(unittest.TestCase):
    def test_programming_and_language_questions_pass(self):
        for q in ("كيف اكتب دالة في بايثون", "ما معنى كلمة الصبر", "كيف اصلح خطأ في كودي",
                  "What is a list in Python?", "اعرب الجملة التالية", "ترجم هذه الجملة للانجليزي", "مرحبا كيف حالك"):
            self.assertTrue(scope.in_scope(q), q)
    def test_clearly_off_domain_is_refused(self):
        for q in ("كيف ابني بيت", "ما هي عاصمة السعودية", "وصفة كبسة دجاج", "ما تشخيص هذا المرض",
                  "كيف اصلح محرك السيارة", "ما هو حكم شرعي في كذا", "سعر الذهب اليوم"):
            self.assertFalse(scope.in_scope(q), q)
    def test_refusal_message_explains_the_specialization(self):
        self.assertIn("البرمجة", scope.REFUSAL_AR); self.assertIn("العربية", scope.REFUSAL_AR); self.assertIn("الإنجليزية", scope.REFUSAL_AR)
    def test_chat_engine_uses_the_guard_before_the_model(self):
        src = (Path(__file__).resolve().parent.parent / "nuwaa" / "conversation" / "chat.py").read_text(encoding="utf-8")
        self.assertIn("scope.guard(q)", src); self.assertIn('route="scope"', src)

if __name__ == "__main__": unittest.main()
