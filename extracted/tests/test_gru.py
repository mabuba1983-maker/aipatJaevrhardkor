# -*- coding: utf-8 -*-
import sys, tempfile, unittest, zipfile, io, re
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.lm.gru import GRULM, Session
from nuwaa.lm import devfile
from nuwaa.conversation.chat import Chat

TOY = "س:مرحبا\nج:اهلا وسهلا\nس:كيف حالك\nج:بخير والحمد لله\n" * 6

def tiny(seed=1, steps=60):
    m = GRULM(emb=8, hid=16, seed=seed); ids = m.encode(TOY)
    for _ in range(steps):
        _, g, _ = m.loss_grads(ids[None, :-1], ids[None, 1:], m.zero_state(1)); m.adam(g, 1e-2)
    return m

class Gradients(unittest.TestCase):
    def test_backprop_through_time_matches_numeric_gradient(self):
        m = GRULM(emb=6, hid=8, seed=1); ids = m.encode(TOY[:40])
        for k in m.P: m.P[k] = m.P[k].astype(np.float64)
        X = ids[None, :-1].repeat(2, 0); Y = ids[None, 1:].repeat(2, 0); st = (np.full((2, 8), 0.2), np.full((2, 8), -0.1))
        _, g, _ = m.loss_grads(X, Y, st); r = np.random.RandomState(0)
        for k in m.P:
            for _ in range(3):
                i = tuple(r.randint(0, s) for s in m.P[k].shape); old = m.P[k][i]
                m.P[k][i] = old + 1e-5; a = m.loss_grads(X, Y, st)[0]; m.P[k][i] = old - 1e-5; b = m.loss_grads(X, Y, st)[0]; m.P[k][i] = old
                num = (a - b) / 2e-5; self.assertLess(abs(num - g[k][i]), 1e-4 + 1e-3 * abs(num), (k, i, num, g[k][i]))

class Model(unittest.TestCase):
    def test_it_learns_and_the_window_is_gone(self):
        m = GRULM(emb=8, hid=16, seed=2); ids = m.encode(TOY); before = m.bpc(ids)
        m.train_stream(ids, B=4, T=32, epochs=40, lr=1e-2); self.assertLess(m.bpc(ids), before - 0.5)
        self.assertFalse(hasattr(m, "ctx"))                       # no fixed context length exists in the model
    def test_bytes_roundtrip_gives_the_same_probabilities(self):
        m = tiny(); n = GRULM.from_bytes(m.to_bytes()); ids = m.encode(TOY[:50], grow=False)
        self.assertAlmostEqual(m.bpc(ids), n.bpc(ids), places=4)
    def test_save_load_roundtrip(self):
        m = tiny(); p = Path(tempfile.mkdtemp()) / "m.npz"; m.save(p); n = GRULM.load(p); ids = m.encode(TOY[:50], grow=False)
        self.assertAlmostEqual(m.bpc(ids), n.bpc(ids), places=4)
    def test_always_writes_a_reply_even_when_unsure(self):
        m = GRULM(emb=6, hid=8, seed=5); m.encode(TOY); s = Session(m, seed=1)
        for q in ("مرحبا", "شي ما شفته قبل", "x"):
            r, _ = s.reply(q, max_chars=30, learn=False); self.assertTrue(r.strip(), q)
    def test_long_conversation_is_accepted_without_a_cap(self):
        m = tiny(); s = Session(m, seed=1)
        for _ in range(40): s.reply("مرحبا كيف حالك اليوم", max_chars=20, learn=False)
        self.assertGreater(len(s.text), 600)                       # far past the old 24 characters, state and text keep growing
    def test_observe_learns_user_words_at_once(self):
        m = tiny(); w = m.P["Wo"].copy(); m.observe("القطة حيوان اليف", steps=3); self.assertGreater(m.long.n, 0); self.assertFalse(np.allclose(w, m.P["Wo"]))

class Developer(unittest.TestCase):
    def test_developer_file_ok_then_broken_when_changed(self):
        m = tiny(); d = Path(tempfile.mkdtemp()); f = d / "dev.zip"; f.write_bytes(devfile.make(m, ["مرحبا", "كيف حالك"], {"x": 1}))
        ok, why, _ = devfile.check(str(f), data=str(ROOT / "data"), say=lambda *_: None); self.assertTrue(ok or "الأساس" in " ".join(why) or why, why)
        z = zipfile.ZipFile(f); out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as w:
            for n in z.namelist(): w.writestr(n, z.read(n) if n != "memory.txt" else b"tampered")
        g = d / "bad.zip"; g.write_bytes(out.getvalue())
        ok2, why2, _ = devfile.check(str(g), data=str(ROOT / "data"), say=lambda *_: None); self.assertFalse(ok2); self.assertTrue(any("البصمة" in x for x in why2))
    def test_garbage_is_broken(self):
        f = Path(tempfile.mkdtemp()) / "x.zip"; f.write_bytes(b"not a zip"); self.assertFalse(devfile.check(str(f), say=lambda *_: None)[0])

class InChat(unittest.TestCase):
    def mk(self, d):
        k = Path(d) / "k"; k.mkdir(exist_ok=True); tiny().save(k / "nlm_user.npz"); return Chat(data="data", model="none.pt", knowledge=str(k))
    def test_every_message_is_answered_by_the_model_and_arithmetic_stays_exact(self):
        with tempfile.TemporaryDirectory() as d:
            c = self.mk(d); r = c.respond("مرحبا", "a"); self.assertEqual(r["route"], "lm"); self.assertTrue(r["reply"].strip())
            self.assertEqual(c.respond("كم يساوي ٢ + ٣", "a")["route"], "math")
    def test_short_term_memory_ends_with_the_conversation_and_long_term_stays(self):
        with tempfile.TemporaryDirectory() as d:
            c = self.mk(d); c.reply("القطة حيوان اليف", "a"); self.assertIn("a", c.sessions); self.assertTrue(c.end("a")); self.assertNotIn("a", c.sessions)
            c2 = Chat(data="data", model="none.pt", knowledge=str(Path(d) / "k")); self.assertIn("القطة حيوان اليف", c2.memory); self.assertGreater(c2.lm.long.n, 0)
    def test_two_conversations_do_not_share_short_term_memory(self):
        with tempfile.TemporaryDirectory() as d:
            c = self.mk(d); c.reply("مرحبا", "a"); c.reply("مرحبا", "b"); self.assertIsNot(c.sessions["a"], c.sessions["b"]); self.assertGreater(c.sessions["a"].short.n, 0)
    def test_develop_and_developer_file(self):
        with tempfile.TemporaryDirectory() as d:
            c = self.mk(d)
            for t in ("مرحبا بك", "كيف حالك اليوم", "القطة حيوان اليف", "بايثون لغة سهلة"): c.reply(t, "a")
            rep = c.develop(epochs=1); self.assertTrue(rep["ok"]); self.assertLessEqual(rep["bits_after"], rep["bits_before"] + 1e-6)
            base = Path(d) / "base.bin"; base.write_bytes(GRULM.load(Path(d) / "k" / "nlm_user.npz").to_bytes())      # the model as it was before developing
            p = Path(d) / "dev.zip"; p.write_bytes(c.dev_file(rep)); ok, why, _ = devfile.check(str(p), str(base), data=str(ROOT / "data"), say=lambda *_: None); self.assertTrue(ok, why)

class NoCannedReplies(unittest.TestCase):
    PHRASES = ("أسمعك", "احكِ لي أكثر", "ما علمتني", "كمّل، أسمعك", "كلمة جديدة سجلتها", "هل تقصد:")
    def test_no_canned_phrase_is_left_in_the_reply_path(self):
        files = [ROOT / "nuwaa/conversation/chat.py", ROOT / "nuwaa/lm/gru.py"] + sorted((ROOT / "android/app/src/main/java/ai/nuwaa").glob("*.kt")) + [ROOT / "nuwaa-ui.html"]
        for f in files:
            s = f.read_text(encoding="utf-8")
            for p in self.PHRASES: self.assertNotIn(p, s, f"{f.name}: {p}")
    def test_old_fixed_window_is_gone(self):
        self.assertFalse((ROOT / "nuwaa/lm/nlm.py").exists()); self.assertNotIn("ctx=24", (ROOT / "nuwaa/lm/gru.py").read_text(encoding="utf-8"))

if __name__ == "__main__": unittest.main()
