# -*- coding: utf-8 -*-
"""Conversation. Every message is answered by the recurrent language model (nuwaa/lm/gru.py) WRITING the reply, character by character.
 * No canned phrase, no lookup, no confidence gate: it always answers (even when it is not sure), and it learns from what it is told with nothing to type.
 * Exact arithmetic is the only tool kept, because a character model cannot be trusted with sums (it is a computation, not a phrase).
 * Short-term memory: one Session per conversation (hidden state + n-gram memory); `end(sid)` drops it.
 * Long-term memory: the weights (knowledge/nlm_user.npz) and everything heard (knowledge/memory.txt); both are loaded again at start.
 * Self-development: `develop()` re-trains on everything heard, keeps the result only if it got better, and `dev_file()` returns the developer file."""
import json, os, time
from collections import Counter, OrderedDict
from pathlib import Path
from ..skills.calc import try_math
from ..lm.gru import GRULM, Session
from ..lm import devfile
from ..skills import scope

MAX_SESSIONS = 64
SAVE_EVERY = 10

class Chat:
    def __init__(self, data="data", model="model.pt", knowledge="knowledge"):
        self.data = data; self.know = Path(knowledge); self.know.mkdir(parents=True, exist_ok=True)
        self.routes = Counter(); self.last = {}; self._trace = []; self.engine = None; self.observed = 0
        self.sessions = OrderedDict(); self.memory = []
        self.base_file = Path(os.environ["NUWAA_WEIGHTS"]) if os.environ.get("NUWAA_WEIGHTS") else Path(__file__).resolve().parents[2] / "weights" / "nlm2.npz"      # a big model on a PC/server: NUWAA_WEIGHTS=path.npz
        self.user_file = self.know / "nlm_user.npz"; self.mem_file = self.know / "memory.txt"
        self.lm = self._load()
    def _load(self):
        lm = None
        for p in (self.user_file, self.base_file):               # what this installation already learned wins over the pretrained start
            if p.exists():
                try: lm = GRULM.load(p); break
                except Exception: lm = None                        # a damaged file never blocks the start
        if lm is None: return None
        if self.mem_file.exists():
            for line in self.mem_file.read_text(encoding="utf-8").splitlines():
                if line.strip(): self.memory.append(line); lm.long.add(line)
        return lm
    # ---------------------------------------------------------------- sessions: short-term memory
    def session(self, sid="default"):
        s = self.sessions.get(sid)
        if s is None:
            if not self.lm: return None
            s = self.sessions[sid] = Session(self.lm)
            while len(self.sessions) > MAX_SESSIONS: self.sessions.popitem(last=False)
        else: self.sessions.move_to_end(sid)
        return s
    def end(self, sid="default"):
        """The conversation ended: its short-term memory is gone. (What was said is already in the long-term memory.)"""
        return self.sessions.pop(sid, None) is not None
    # ---------------------------------------------------------------- one message
    def _tr(self, stage, detail=""): self._trace.append({"stage": stage, "detail": detail})
    def reply(self, q, sid="default"): return self.respond(q, sid)["reply"]
    def respond(self, q, sid="default", can_teach=True):
        """Returns dict(reply, route, score, id, trace). route is 'math' or 'lm'; score = mean probability the model gave its own characters."""
        self._trace = []; self._tr("received", f"{len(q)} chars, session={sid[:12]}")
        q = q.strip(); s = self.session(sid)
        out = scope.guard(q)
        if out is not None:
            self._tr("scope", "out of specialization: programming / Arabic / English only")
            if s: s._feed("س:" + q.replace("\n", " ¶ ") + "\nج:" + out.replace("\n", "¶") + "\n")
            return dict(reply=out, route="scope", score=1.0, id="")
        m = try_math(q)
        if m:
            self._tr("math", "exact arithmetic")
            if s: s._feed("س:" + q.replace("\n", " ¶ ") + "\nج:" + m.replace("\n", "¶") + "\n")     # the conversation still remembers it
            r = dict(reply=m, route="math", score=1.0, id="")
        elif s is None:
            r = dict(reply="النموذج غير محمّل: لم يُدرَّب بعد (weights/nlm2.npz).", route="none", score=0.0, id="")
        else:
            out, tr = s.reply(q, learn=False); score = sum(tr) / len(tr) if tr else 0.0
            self._tr("lm", f"wrote {len(out)} chars, mean confidence {score:.2f}")
            self._hear(q, s)
            r = dict(reply=out, route="lm", score=score, id="")
        r["trace"] = self._trace; self.last = r; self.routes["total"] += 1; self.routes[r["route"]] += 1
        return r
    def _hear(self, q, s):
        """Learning by listening: long-term memory at once, weights by a few small steps. Nothing to type, nothing announced."""
        lm = self.lm; lm.observe(q); s.short.add("س:" + q); self.memory.append(q.replace("\n", " ")); self.observed += 1
        with open(self.mem_file, "a", encoding="utf-8") as f: f.write(q.replace("\n", " ") + "\n")
        if self.observed % SAVE_EVERY == 0: self.save()
    def save(self):
        if self.lm: self.lm.save(self.user_file)
    def learn(self, q, a):
        """Admin teaching through the API: the pair is trained on exactly like everything else."""
        if not self.lm: return False
        self.lm.observe_pair(q, a); self.save()
        p = Path(self.data) / "user_feedback.jsonl"; p.parent.mkdir(parents=True, exist_ok=True)       # queued for the next training run (pretrain_gru reads it)
        with open(p, "a", encoding="utf-8") as f: f.write(json.dumps({"user": q, "bot": a}, ensure_ascii=False) + "\n")
        return True
    # ---------------------------------------------------------------- self-development
    def develop(self, epochs=3):
        """Re-read everything heard and train on it. Returns a report; the weights are rolled back if they got worse."""
        if not self.lm: return dict(ok=False, message="النموذج غير محمّل")
        try:
            from ..lm.corpus import all_pairs
            import random; P = all_pairs(self.data); rehearse = random.Random(5).sample(P, min(120, len(P))) if P else None
        except Exception: rehearse = None                                  # no data folder on this machine: develop without rehearsal
        before, after = self.lm.develop(self.memory[-400:], epochs=epochs, rehearse=rehearse); self.save()
        return dict(ok=True, heard=len(self.memory), bits_before=round(before, 3), bits_after=round(after, 3), params=self.lm.n_params(), memory_chars=self.lm.long.n)
    def dev_file(self, report=None):
        """The developer file (bytes of a zip): new weights + long-term memory + report. Whoever receives it runs `python -m nuwaa.lm.devfile check FILE`."""
        return devfile.make(self.lm, self.memory, report or self.develop())
    def engine_report(self):
        return dict(loaded=self.lm is not None, kind="GRU (recurrent, unbounded context)", params=self.lm.n_params() if self.lm else 0, heard=len(self.memory), sessions=len(self.sessions))
