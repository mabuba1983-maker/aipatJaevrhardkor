import sqlite3, time
class Memory:
    def __init__(self, path="memory.db"):
        self.db = sqlite3.connect(path); self.db.execute("create table if not exists facts(k text, v text, t real)"); self.db.commit()
    def remember(self, k, v): self.db.execute("insert into facts values(?,?,?)", (k, v, time.time())); self.db.commit()
    def recall(self, k): return [r[0] for r in self.db.execute("select v from facts where k=? order by t desc", (k,))]
