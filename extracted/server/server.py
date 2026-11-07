# -*- coding: utf-8 -*-
"""Nuwaa web server: web chat page + JSON API. Python standard library only (no pip install needed except PyTorch if you serve a trained model).
  python server/server.py                       -> http://0.0.0.0:8000
Environment: NUWAA_PORT, NUWAA_ADMIN_TOKEN (needed to teach), NUWAA_MODEL (path to model.pt), NUWAA_RATE (requests/min per IP), NUWAA_LOG=1 (log questions: off by default, privacy)."""
import hashlib, hmac, json, os, sys, threading, time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nuwaa.conversation.chat import Chat
from nuwaa.mind.mind import Mind
from nuwaa.mind import develop as mind_dev

MAX_BODY, MAX_Q, MAX_FILES_BODY = 16_384, 2000, 4_000_000
MAX_TEACH_BODY, MAX_TEACH_Q = 2_000_000, 400_000      # one message may carry thousands of lessons (admin only)

class App:
    def __init__(self, data_dir=None, model=None, knowledge=None, admin_token=None, rate=30, log_file=None, root=None):
        self.data = str(data_dir or ROOT / "data"); self.model = str(model or os.environ.get("NUWAA_MODEL") or ROOT / "model.pt")
        self.knowledge = str(knowledge or ROOT / "knowledge"); self.admin = admin_token if admin_token is not None else os.environ.get("NUWAA_ADMIN_TOKEN", "")
        self.rate = int(os.environ.get("NUWAA_RATE", rate)); self.log_file = log_file
        self.root = str(root or ROOT); self.mind_busy = False
        self.lock = threading.Lock(); self.hits = defaultdict(deque); self._chat = None; self._mtime = None; self.load_error = None
    def chat(self):
        """Rebuilds the engine when model.pt changes, so a newly accepted model is used without restarting the server."""
        m = Path(self.model); mt = m.stat().st_mtime if m.exists() else None
        if self._chat is None or mt != self._mtime:
            try: self._chat = Chat(self.data, self.model, self.knowledge); self.load_error = None
            except Exception as e:                      # e.g. PyTorch missing: keep serving from the knowledge base
                self.load_error = f"{type(e).__name__}: {e}"; self._chat = Chat(self.data, "__none__.pt", self.knowledge)
            self._mtime = mt
        return self._chat
    def allowed(self, ip):
        now = time.monotonic(); q = self.hits[ip]
        while q and now - q[0] > 60: q.popleft()
        if len(q) >= self.rate: return False
        q.append(now); return True
    def health(self):
        with self.lock:
            c = self.chat(); return {"ok": True, "model_loaded": c.lm is not None, "model_error": self.load_error, "knowledge_items": len(c.memory),
                                     "routes": dict(c.routes), "engine": c.engine_report()}
    def reply_info(self, q, sid="web", can_teach=False):
        with self.lock: info = self.chat().respond(q, sid, can_teach)
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f: f.write(json.dumps({"t": int(time.time()), "q": q, "a": info["reply"], "route": info["route"]}, ensure_ascii=False) + "\n")
        return info
    def reply(self, q, sid="web"): return self.reply_info(q, sid)["reply"]
    def teach(self, q, a):
        with self.lock: self.chat().learn(q, a)
    # ---- the Mind: learns words + programming skills; study/develop run in the background (slow on purpose: accuracy, not speed) ----
    def mind(self): return Mind(self.root)
    def mind_status(self):
        m = self.mind(); st = m.status(); log = Path(self.root) / "mind_log.jsonl"; last = None
        if log.exists() and log.stat().st_size:
            try: last = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
            except Exception: pass
        return {**st, "busy": self.mind_busy, "last": last, "competence": m.competence() if not self.mind_busy else None}
    def save_code_inbox(self, files):
        d = Path(self.root) / "learned" / "code_inbox"; d.mkdir(parents=True, exist_ok=True); n = 0
        for name, text in files:
            if len(list(d.glob("*.txt"))) >= 50 or len(text) > 300_000 or not name.lower().endswith(".py"): continue
            (d / (hashlib.sha1(text.encode()).hexdigest()[:12] + ".txt")).write_text(text, encoding="utf-8"); n += 1
        return n
    def mind_start(self, mode, approve, rounds=3):
        with self.lock:
            if self.mind_busy: return False
            self.mind_busy = True
        def job():
            try:
                if mode == "study": mind_dev.press(self.root, "server"); mind_dev.study(self.root, approve, say=lambda *_: None)
                else: mind_dev.button(self.root, approve, max(1, min(int(rounds), 20)), say=lambda *_: None)
            except Exception as e: mind_dev._log(self.root, {"mode": mode, "decision": "error", "message": type(e).__name__ + ": " + str(e)}, say=lambda *_: None)
            finally: self.mind_busy = False
        threading.Thread(target=job, daemon=True).start(); return True

def make_server(app, host="0.0.0.0", port=8000):
    index = (Path(__file__).parent / "index.html").read_bytes()
    class H(BaseHTTPRequestHandler):
        server_version = "Nuwaa"
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", os.environ.get("NUWAA_CORS", "*")); self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(body)
        def _ip(self): return self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        def _json(self, limit=MAX_BODY):
            try: n = int(self.headers.get("Content-Length", "0"))
            except ValueError: n = -1
            if n < 0 or n > limit: self._send(413, {"error": "الطلب كبير"}); return None
            try:
                d = json.loads(self.rfile.read(n).decode("utf-8")); assert isinstance(d, dict); return d
            except Exception: self._send(400, {"error": "صيغة غير صحيحة"}); return None
        def do_OPTIONS(self): self._send(204, b"", "text/plain")
        def do_GET(self):
            if self.path in ("/", "/index.html"): self._send(200, index, "text/html; charset=utf-8")
            elif self.path == "/api/health": self._send(200, app.health())
            elif self.path == "/api/mind": self._send(200, app.mind_status())
            else: self._send(404, {"error": "غير موجود"})
        def do_POST(self):
            if self.path not in ("/api/chat", "/api/teach", "/api/mind/ask", "/api/mind/study", "/api/mind/develop", "/api/mind/teach", "/api/mind/review", "/api/mind/upload"): return self._send(404, {"error": "غير موجود"})
            if not app.allowed(self._ip()): return self._send(429, {"error": "طلبات كثيرة، انتظر دقيقة"})
            tok0 = self.headers.get("Authorization", "").removeprefix("Bearer ").strip(); is_admin = bool(app.admin) and hmac.compare_digest(tok0, app.admin)
            d = self._json(MAX_FILES_BODY if self.path in ("/api/mind/review", "/api/mind/upload") else (MAX_TEACH_BODY if (self.path == "/api/chat" and is_admin) else MAX_BODY))
            if d is None: return
            if self.path in ("/api/mind/review", "/api/mind/upload"):
                from nuwaa.mind import review as rv
                import base64
                try:
                    files = [(str(f["name"])[:200], str(f["text"])) for f in d.get("files", [])[:rv.MAX_FILES] if isinstance(f, dict)]
                    if isinstance(d.get("zip_b64"), str): files += rv.read_zip(base64.b64decode(d["zip_b64"]))
                except Exception: return self._send(400, {"error": "ملف غير صالح"})
                if not files: return self._send(400, {"error": "ما وصلني ملفات"})
                if self.path == "/api/mind/review":                      # read-only static analysis: nothing is ever executed
                    rep = rv.review_files(files); rep["text"] = rv.format_report(rep); return self._send(200, rep)
                tok = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                if not app.admin or not hmac.compare_digest(tok, app.admin): return self._send(403, {"error": "للمشرف فقط"})
                saved = app.save_code_inbox(files); return self._send(200, {"saved": saved, "message": "انحفظت. بتتعلم منها في دورة التطوير القادمة (يتحقق من كل دالة قبل ما يعتمدها)."})
            if self.path == "/api/chat":
                q = d.get("message")
                if not isinstance(q, str) or not q.strip(): return self._send(400, {"error": "اكتب رسالة"})
                if len(q) > (MAX_TEACH_Q if is_admin else MAX_Q): return self._send(413, {"error": "الرسالة طويلة"})
                sid = d.get("session") if isinstance(d.get("session"), str) and 0 < len(d["session"]) <= 64 else self._ip()    # follow-up context is kept per session, never shared between users
                try:
                    info = app.reply_info(q.strip(), sid, is_admin); out = {"reply": info["reply"]}
                    if d.get("debug") is True: out.update(route=info["route"], score=round(info["score"], 2), id=info["id"], trace=info.get("trace", []))
                    return self._send(200, out)
                except Exception as e: return self._send(500, {"error": "خطأ داخلي: " + type(e).__name__})
            if self.path == "/api/mind/ask":
                q = d.get("message")
                if not isinstance(q, str) or not q.strip() or len(q) > MAX_Q: return self._send(400, {"error": "اكتب رسالة"})
                with app.lock: return self._send(200, app.mind().ask(q.strip()))
            tok = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()          # /api/teach: admin only, so strangers cannot poison the model
            if not app.admin or not hmac.compare_digest(tok, app.admin): return self._send(403, {"error": "غير مصرح"})
            if self.path in ("/api/mind/study", "/api/mind/develop"):        # the button: admin only, one job at a time
                started = app.mind_start("study" if self.path.endswith("study") else "develop", d.get("approve") is True, d.get("rounds", 3))
                return self._send(200 if started else 409, {"started": started, "message": "بدأ. ياخذ وقت لأن الهدف الدقة مو السرعة." if started else "فيه دورة شغالة الحين"})
            if self.path == "/api/mind/teach":
                try: tid = app.mind().add_wish(str(d.get("desc", ""))[:300], d.get("examples"), d.get("id")); return self._send(200, {"ok": True, "id": tid})
                except Exception as e: return self._send(400, {"error": "مثال غير صالح: " + str(e)[:120]})
            q, a = d.get("question"), d.get("answer")
            if not (isinstance(q, str) and isinstance(a, str) and q.strip() and a.strip()) or len(q) > MAX_Q or len(a) > MAX_Q: return self._send(400, {"error": "سؤال وجواب مطلوبان"})
            app.teach(q.strip(), a.strip()); self._send(200, {"ok": True})
    return ThreadingHTTPServer((host, port), H)

if __name__ == "__main__":
    port = int(os.environ.get("NUWAA_PORT", "8000")); app = App(log_file=str(ROOT / "chat_log.jsonl") if os.environ.get("NUWAA_LOG") == "1" else None)
    if not app.admin: print("NUWAA_ADMIN_TOKEN غير مضبوط: التعليم عبر الـ API معطّل.")
    print("Nuwaa server:", app.health(), f"-> http://0.0.0.0:{port}"); make_server(app, "0.0.0.0", port).serve_forever()
