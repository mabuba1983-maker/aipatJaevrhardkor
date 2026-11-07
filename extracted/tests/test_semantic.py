# -*- coding: utf-8 -*-
"""Semantic (numpy meaning engine): learns from data/, must beat the plain matcher on unseen wordings and must NOT answer out-of-domain questions."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from nuwaa.understand.semantic import Semantic
from nuwaa.memory.kb import KB

ITEMS = [json.loads(l) for l in (ROOT / "data" / "kb" / "kb.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
OOD = ["كم عمر القمر", "ما عاصمة فرنسا", "من اخترع الكهرباء", "كيف الطقس اليوم", "وش احسن مطعم", "كم سعر الذهب اليوم", "كيف اطبخ الكبسة", "ما لون السماء"]

def split(hold):
    tr, te = [], []
    for d in ITEMS:
        qs = d["q"]
        if len(qs) >= 3:
            j = min(hold, len(qs) - 1); te.append((qs[j], d["id"])); tr.append(([q for k, q in enumerate(qs) if k != j], d["a"], d["id"]))
        else: tr.append((qs, d["a"], d["id"]))
    return tr, te

class TestSemantic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tr, cls.te = split(0); cls.f = Semantic().fit(cls.tr)
    def test_beats_plain_matcher_on_unseen_wordings(self):
        kb = KB()
        for qs, a, i in self.tr: kb.add(qs, a, i)
        old = sum((kb.best(q)[0] or {}).get("id") == i for q, i in self.te)
        new = sum(((self.f.understand(q, 1) or [(0, None, 0)])[0][1]) == i for q, i in self.te)
        self.assertGreater(new, old * 1.4, (old, new))
    def test_sure_answers_are_mostly_right(self):
        sure = ok = 0
        for q, i in self.te:
            p, s, st = self.f.answer(q)
            if st == "sure": sure += 1; ok += p == i
        self.assertGreater(sure / len(self.te), 0.35); self.assertGreater(ok / sure, 0.72)
    def test_never_confident_out_of_domain(self):
        for q in OOD: self.assertNotEqual(self.f.answer(q)[2], "sure", q)
    def test_exact_question_is_found(self):
        d = ITEMS[10]; full = Semantic().fit([(x["q"], x["a"], x["id"]) for x in ITEMS])
        p, s, st = full.answer(d["q"][0]); self.assertEqual((p, st), (d["id"], "sure"))
    def test_deterministic(self):
        a = Semantic().fit(self.tr).understand("كيف اطبع نص بايثون", 1)[0][:1]; b = Semantic().fit(self.tr).understand("كيف اطبع نص بايثون", 1)[0][:1]
        self.assertEqual(a, b)
if __name__ == "__main__": unittest.main()
