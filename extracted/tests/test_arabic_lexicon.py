# -*- coding: utf-8 -*-
import json, re, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from nuwaa.memory.kb import KB, HIGH, is_meaning, MEANING, tokens
from nuwaa.conversation.chat import Chat
import kb_arabic

class Lex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = KB().load_jsonl(ROOT / "data/kb/lexicon.jsonl"); cls.rows = kb_arabic.read_lexicon()
        cls.main = KB().load_jsonl(ROOT / "data/kb/kb.jsonl")
    def test_lexicon_file_matches_the_source_list(self):
        self.assertGreaterEqual(len(self.rows), 100)
        n = len((ROOT / "data/kb/lexicon.jsonl").read_text(encoding="utf-8").splitlines())
        self.assertEqual(n, len(self.rows) + 5)           # + 5 Gulf words
        self.assertFalse(any(json.loads(l)["id"].startswith("ar_w") for l in (ROOT / "data/kb/kb.jsonl").read_text(encoding="utf-8").splitlines()))
    def test_every_word_is_answered_with_its_own_entry(self):
        by_answer = {json.loads(l)["a"]: json.loads(l)["id"] for l in (ROOT / "data/kb/lexicon.jsonl").read_text(encoding="utf-8").splitlines()}
        bad = []
        for w, mean, syn, ant, ex in self.rows:
            want = by_answer[kb_arabic.lexicon_answer(w, mean, syn, ant, ex)]
            for q in (f"ما معنى كلمة {w}", f"ماذا تعني كلمة {w}"):
                self.assertTrue(is_meaning(q), q)
                r = self.lex.search(q, 1)
                if not r or r[0][1]["id"] != want or r[0][0] < HIGH: bad.append((q, r[0][1]["id"] if r else None))
        self.assertEqual(bad, [], bad[:10])
    def test_synonym_and_antonym_questions(self):
        s, it = self.lex.search("ما ضد كريم", 1)[0]; self.assertIn("بخيل", it["a"]); self.assertGreaterEqual(s, HIGH)
        s, it = self.lex.search("ما مرادف شجاع", 1)[0]; self.assertIn("جريء", it["a"]); self.assertGreaterEqual(s, HIGH)
    def test_dictionary_is_used_only_for_meaning_questions(self):
        # these programming questions contain dictionary words (الخطأ، كلمة، سريع...) and must NOT be answered from the dictionary
        for q in ("كيف اتجاوز خطأ NameError", "كيف اعرف عدد تكرار كل كلمة", "كيف اعرف ان كودي سريع", "كيف اكتب دالة في بايثون"):
            self.assertFalse(is_meaning(q), q)
    def test_grammar_questions(self):
        for q, word in (("ما الفرق بين همزة الوصل والقطع", "همزة القطع"), ("كم عدد حروف اللغة العربية", "28"), ("ما هي كان واخواتها", "أصبح"),
                        ("ما هي الحروف الشمسية", "الشمس"), ("ما الفرق بين الفصحى والعامية", "اللهجات")):
            s, it = self.main.search(q, 1)[0]; self.assertIn(word, it["a"], q)
    def test_kotlin_mirror(self):
        k = (ROOT / "android/app/src/main/java/ai/nuwaa/Kb.kt").read_text(encoding="utf-8")
        got = set(re.search(r"private val meaning = setOf\(([^)]*)\)", k).group(1).replace('"', "").replace(" ", "").split(","))
        self.assertEqual(got, MEANING)
    def test_lexicon_is_in_training_data_but_not_in_search_data(self):
        t = (ROOT / "data/train_only/lexicon_chat.jsonl").read_text(encoding="utf-8")
        self.assertIn("ما معنى كلمة كريم", t)
        self.assertFalse((ROOT / "data/lexicon_chat.jsonl").exists())
if __name__ == "__main__": unittest.main()
