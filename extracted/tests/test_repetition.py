# -*- coding: utf-8 -*-
"""Regression: the model must not echo the user's earlier messages or repeat its own earlier replies."""
import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nuwaa.lm.gru import GRULM, Session

W = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weights", "nlm2.npz")

class Repetition(unittest.TestCase):
    def test_dedupe_drops_repeated_sentences(self):
        self.assertEqual(Session.dedupe("أهلا بك يا صديقي. أهلا بك يا صديقي. كيف حالك؟"), "أهلا بك يا صديقي. كيف حالك؟")
    @unittest.skipUnless(os.path.exists(W), "weights missing")
    def test_hearing_messages_does_not_make_it_echo(self):
        m = GRULM.load(W); s = Session(m, seed=5); msgs = ["احتاج اتعلم بايثون", "ايش افضل طريقة", "كيف اكتب دالة", "شرح لي المتغيرات"]
        for q in msgs:
            out, _ = s.reply(q, learn=False); m.observe(q); s.short.add("س:" + q)
            for old in msgs:
                if old != q: self.assertNotEqual(out.strip(), old, "echoed an earlier user message")
    @unittest.skipUnless(os.path.exists(W), "weights missing")
    def test_no_long_piece_twice_in_one_reply(self):
        m = GRULM.load(W)
        for q in ["ما هي بايثون", "كيف اكتب حلقة for", "اشرح الدوال"]:
            out, _ = Session(m, seed=2).reply(q, learn=False)
            if "```" in out: continue                                  # code legitimately repeats short pieces
            pieces = [out[i:i + 24] for i in range(len(out) - 24)]
            self.assertEqual(len(pieces), len(set(pieces)))
if __name__ == "__main__": unittest.main()
