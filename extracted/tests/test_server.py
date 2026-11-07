# -*- coding: utf-8 -*-
import json, shutil, sys, tempfile, threading, unittest, urllib.error, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "server"))
import server as srv, improve as imp
from nuwaa.selfimprove import cycle

def call(port, path, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST" if data is not None else "GET", headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()

class Server(unittest.TestCase):
    def start(self, **kw):
        self.tmp = Path(tempfile.mkdtemp()); shutil.copytree(ROOT / "data", self.tmp / "data")
        self.app = srv.App(self.tmp / "data", self.tmp / "none.pt", self.tmp / "kn", **kw)
        self.httpd = srv.make_server(self.app, "127.0.0.1", 0); threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]; self.addCleanup(self.httpd.shutdown); self.addCleanup(self.httpd.server_close)
    def test_page_health_chat(self):
        self.start(admin_token="s3cret")
        c, b = call(self.port, "/"); self.assertEqual(c, 200); self.assertIn("<html", b.decode("utf-8")); self.assertNotIn("http://", b.decode("utf-8").replace("http://127", ""))   # page loads nothing external
        c, b = call(self.port, "/api/health"); h = json.loads(b); self.assertTrue(h["ok"]); self.assertTrue(h["model_loaded"]); self.assertGreaterEqual(h["knowledge_items"], 0)
        c, b = call(self.port, "/api/chat", {"message": "كم يساوي ٢٥ + ١٧"}); self.assertIn("42", json.loads(b)["reply"])
        c, b = call(self.port, "/api/chat", {"message": "كيف اكتب حلقة for في بايثون"}); self.assertTrue(json.loads(b)["reply"].strip())      # the model writes it: always something
        c, b = call(self.port, "/api/chat", {"message": "ما هو سعر الذهب اليوم"}); self.assertTrue(json.loads(b)["reply"].strip())
    def test_bad_input(self):
        self.start()
        self.assertEqual(call(self.port, "/api/chat", raw=b"not json")[0], 400)
        self.assertEqual(call(self.port, "/api/chat", {"message": ""})[0], 400)
        self.assertEqual(call(self.port, "/api/chat", {"message": "x" * 2001})[0], 413)
        self.assertEqual(call(self.port, "/api/chat", raw=b"{" + b" " * 20000 + b"}")[0], 413)
        self.assertEqual(call(self.port, "/nope")[0], 404)
    def test_teach_is_admin_only(self):
        self.start(admin_token="s3cret"); body = {"question": "ما اسم مشروعي الخاص", "answer": "مشروعك اسمه قمر"}
        self.assertEqual(call(self.port, "/api/teach", body)[0], 403); self.assertEqual(call(self.port, "/api/teach", body, token="wrong")[0], 403)
        self.assertEqual(call(self.port, "/api/teach", body, token="s3cret")[0], 200)
        self.assertIn("قمر", json.loads(call(self.port, "/api/chat", {"message": "ما اسم مشروعي الخاص"})[1])["reply"])
        self.assertTrue((self.tmp / "data" / "user_feedback.jsonl").exists())            # queued for the next training run
    def test_teach_disabled_without_token(self):
        self.start(admin_token=""); self.assertEqual(call(self.port, "/api/teach", {"question": "a", "answer": "b"}, token="")[0], 403)
    def test_rate_limit(self):
        self.start(rate=3); codes = [call(self.port, "/api/chat", {"message": "مرحبا"})[0] for _ in range(5)]; self.assertEqual(codes, [200, 200, 200, 429, 429])
    def test_questions_not_logged_by_default(self):
        self.start(); call(self.port, "/api/chat", {"message": "مرحبا"}); self.assertIsNone(self.app.log_file); self.assertFalse((ROOT / "chat_log.jsonl").exists())

class Improve(unittest.TestCase):
    def setUp(self):
        self.r = Path(tempfile.mkdtemp()); (self.r / "data").mkdir(); self.orig = cycle.run_cycle; self.addCleanup(lambda: setattr(cycle, "run_cycle", self.orig))
        (self.r / "stage_artifacts" / "s2m").mkdir(parents=True); (self.r / "stage_artifacts" / "s2m" / "model.pt").write_bytes(b"NEW")
        self.serve = self.r / "served" / "model.pt"; self.serve.parent.mkdir(); self.serve.write_bytes(b"OLD")
    def test_accepted_swaps_model_and_cleans_feedback(self):
        rows = [json.dumps({"user": f"q{i}", "bot": "a"}) for i in range(3000)] + [json.dumps({"user": "q1", "bot": "a"}), "garbage"]
        (self.r / "data" / "user_feedback.jsonl").write_text("\n".join(rows), encoding="utf-8")
        cycle.run_cycle = lambda root, steps, approve, stage: (self.assertTrue((self.r / "self_improve_press.json").exists()), {"stage": "s2m", "decision": "accepted"})[1]
        rec = imp.improve(self.r, "s2m", 10, True, self.serve)
        self.assertEqual(self.serve.read_bytes(), b"NEW"); self.assertEqual(rec["feedback_pairs"], 3000)          # kept all 3000 (not just the last 2000), dropped duplicate + garbage
    def test_rejected_keeps_old_model(self):
        cycle.run_cycle = lambda *a: {"stage": "s2m", "decision": "kept previous"}
        imp.improve(self.r, "s2m", 10, True, self.serve); self.assertEqual(self.serve.read_bytes(), b"OLD")
    def test_cycle_refuses_without_press(self):
        with self.assertRaises(PermissionError): self.orig(str(self.r), 1, False, "s2m")

if __name__ == "__main__": unittest.main()
