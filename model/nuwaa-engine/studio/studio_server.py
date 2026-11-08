# -*- coding: utf-8 -*-
"""Local Studio backend. Zero extra dependencies (stdlib only).
Run: python studio/studio_server.py --model model.pt
Then open http://localhost:8765/ (or point the TV page at this machine's LAN IP, see studio/tv_host.html).
"""
import argparse, json, os, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nuwaa.core.engine import Engine
from nuwaa.core.self_correct import generate_with_feedback
from nuwaa.sandbox.snippet import run_snippet

ROOT = Path(__file__).resolve().parent
FILES_DIR = ROOT / "studio_files"
FILES_DIR.mkdir(exist_ok=True)

ENGINE = None  # lazily loaded; None until --model is given and the file exists

# "watch it work" jobs: each self-correct run is a background thread that appends real, timestamped
# progress lines (attempt N, the code it just wrote, the real error, retrying...) to JOBS[id]["log"].
# The TV (which is just mirroring your phone, per your last message) shows this live via polling.
JOBS = {}
JOBS_LOCK = threading.Lock()


def _run_job(job_id, prompt, max_retries, max_new):
    def log(line):
        with JOBS_LOCK:
            JOBS[job_id]["log"].append({"t": time.time(), "line": line})
    try:
        log(f"بدأت المهمة... الطلب: {prompt[:200]}")
        result = generate_with_feedback(ENGINE, prompt, max_retries=max_retries, max_new=max_new, log=log)
        with JOBS_LOCK:
            JOBS[job_id]["done"] = True
            JOBS[job_id]["result"] = result
        log("انتهت المهمة. ok=" + str(result["ok"]))
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id]["done"] = True
            JOBS[job_id]["error"] = str(e)
        log("خطأ غير متوقع: " + str(e))


def load_engine(model_path):
    global ENGINE
    try:
        ENGINE = Engine(model_path)
        print(f"engine loaded from {model_path}")
    except FileNotFoundError:
        ENGINE = None
        print(f"WARNING: no weights at {model_path} — chat/preview-from-model will say so until you train one.")


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/studio.html":
            return self._serve_file(ROOT / "studio.html", "text/html")
        if self.path == "/api/list_files":
            return self._json({"files": sorted(p.name for p in FILES_DIR.iterdir() if p.is_file())})
        if self.path.startswith("/api/self_correct/log"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            job_id = (q.get("job_id") or [""])[0]
            since = int((q.get("since") or ["0"])[0])
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if not job:
                    return self._json({"error": "unknown job_id"}, 404)
                new_lines = job["log"][since:]
                return self._json({"lines": new_lines, "next": since + len(new_lines),
                                    "done": job["done"], "result": job["result"], "error": job["error"]})
        if self.path.startswith("/api/file/"):
            name = self.path[len("/api/file/"):]
            p = FILES_DIR / name
            if ".." in name or not p.exists():
                return self._json({"error": "not found"}, 404)
            return self._json({"name": name, "content": p.read_text(encoding="utf-8")})
        self._json({"error": "not found"}, 404)

    def _serve_file(self, path, mime):
        if not path.exists():
            return self._json({"error": f"missing {path.name}"}, 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            data = self._read_json()
        except Exception as e:
            return self._json({"error": f"bad json: {e}"}, 400)

        if self.path == "/api/chat":
            text = data.get("text", "")
            if ENGINE is None:
                return self._json({"reply": "ما فيه نموذج مدرب محمّل حاليا — درّب واحد أو مرر --model لملف صحيح.", "has_engine": False})
            reply = ENGINE.reply(text, max_new=data.get("max_new", 20000),
                                  repetition_penalty=data.get("repetition_penalty", 1.3),
                                  no_repeat_ngram=data.get("no_repeat_ngram", 4))
            return self._json({"reply": reply, "has_engine": True})

        if self.path == "/api/chat_image":
            # data: {"text": "...", "image_path": "/abs/path/on/this/machine.jpg"} -- crude, low-quality vision; see vision.py
            if ENGINE is None:
                return self._json({"reply": "ما فيه نموذج مدرب محمّل حاليا.", "has_engine": False})
            try:
                reply = ENGINE.reply_with_image(data.get("text", ""), data.get("image_path", ""),
                                                 image_size=data.get("image_size", 16))
                return self._json({"reply": reply, "has_engine": True})
            except Exception as e:
                return self._json({"error": str(e)}, 400)

        if self.path == "/api/run_python":
            code = data.get("code", "")
            result = run_snippet(code, timeout=data.get("timeout", 10))
            return self._json(result)

        if self.path == "/api/self_correct":
            # synchronous, one-shot (no live log) — kept for scripting; the UI uses /start + /log instead.
            if ENGINE is None:
                return self._json({"error": "no engine loaded"}, 400)
            result = generate_with_feedback(ENGINE, data.get("prompt", ""),
                                             max_retries=data.get("max_retries", 3),
                                             max_new=data.get("max_new", 20000), log=lambda *_: None)
            return self._json(result)

        if self.path == "/api/self_correct/start":
            if ENGINE is None:
                return self._json({"error": "no engine loaded"}, 400)
            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[job_id] = {"log": [], "done": False, "result": None, "error": None}
            threading.Thread(target=_run_job, args=(job_id, data.get("prompt", ""),
                              data.get("max_retries", 3), data.get("max_new", 20000)), daemon=True).start()
            return self._json({"job_id": job_id})

        if self.path == "/api/create_file":
            name = data.get("filename", "").strip()
            content = data.get("content", "")
            if not name or "/" in name or "\\" in name or ".." in name:
                return self._json({"error": "اسم ملف غير صالح"}, 400)
            (FILES_DIR / name).write_text(content, encoding="utf-8")
            return self._json({"ok": True, "name": name})

        self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass  # keep the console clean; remove this to debug


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="model.pt")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0", help="0.0.0.0 so the TV/other devices on your LAN can reach it")
    a = ap.parse_args()
    load_engine(a.model)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Studio server on http://{a.host}:{a.port}  (open http://<this-PC-LAN-IP>:{a.port} from the TV)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
