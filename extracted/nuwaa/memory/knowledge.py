"""Unlimited-by-design learning store: everything the user teaches goes to disk in SQLite FTS5 shards.
A new shard file starts every `shard_rows` rows, so no single file grows without bound; the only limit is free disk.
(The model's WEIGHTS stay a fixed size per stage; what it learns from the user lives here and is searched, not memorised.)"""
import re, sqlite3, time
from pathlib import Path

def tokens(s): return re.findall(r"\w+", s.lower())

class KnowledgeStore:
    def __init__(self, root="knowledge", shard_rows=1_000_000):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True); self.shard_rows = shard_rows
        if not list(self.root.glob("shard_*.db")): self._open(0).close()
    def _path(self, i): return self.root / f"shard_{i:05d}.db"
    def _open(self, i):
        db = sqlite3.connect(self._path(i))
        db.execute("create virtual table if not exists k using fts5(question, answer, source unindexed, t unindexed)"); db.commit(); return db
    def shards(self): return sorted(self.root.glob("shard_*.db"))
    def count(self):
        n = 0
        for p in self.shards():
            db = sqlite3.connect(p); n += db.execute("select count(*) from k").fetchone()[0]; db.close()
        return n
    def add(self, question: str, answer: str, source="user"):
        i = len(self.shards()) - 1; db = self._open(i)
        if db.execute("select count(*) from k").fetchone()[0] >= self.shard_rows: db.close(); i += 1; db = self._open(i)
        db.execute("insert into k values(?,?,?,?)", (question, answer, source, time.time())); db.commit(); db.close()
    def add_text(self, text: str, source="user"): self.add("", text, source)
    def search(self, query: str, k=3):
        toks = tokens(query)
        if not toks: return []
        q = " OR ".join('"%s"' % t.replace('"', "") for t in toks); hits = []
        for p in self.shards():
            db = sqlite3.connect(p)
            hits += db.execute("select question, answer, source, bm25(k) from k where k match ? order by bm25(k) limit ?", (q, k)).fetchall(); db.close()
        hits.sort(key=lambda h: h[3]); return hits[:k]
