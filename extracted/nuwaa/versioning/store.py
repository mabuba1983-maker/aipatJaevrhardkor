"""Versioned snapshots with SHA-256 integrity and rollback. The BASE version is only changed by a human."""
import hashlib, json, shutil, time
from pathlib import Path

def _hash_tree(p: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(x for x in p.rglob("*") if x.is_file()):
        h.update(str(f.relative_to(p)).encode()); h.update(f.read_bytes())
    return h.hexdigest()

class VersionStore:
    def __init__(self, root="versions"):
        self.root = Path(root); self.root.mkdir(exist_ok=True)
        self.meta = self.root / "meta.json"
        if not self.meta.exists(): self.meta.write_text(json.dumps({"current": None, "history": []}))
    def _m(self): return json.loads(self.meta.read_text())
    def _save(self, m): self.meta.write_text(json.dumps(m, indent=2))
    def snapshot(self, src: str, note: str, approved_by: str) -> str:
        if approved_by not in ("human", "validator+human"):
            raise PermissionError("only a human can promote a version")
        src = Path(src); vid = f"v{len(self._m()['history']) + 1:04d}"
        dst = self.root / vid; shutil.copytree(src, dst)
        m = self._m(); m["history"].append({"id": vid, "note": note, "time": time.time(), "sha": _hash_tree(dst)}); m["current"] = vid
        self._save(m); return vid
    def verify(self, vid: str) -> bool:
        e = next(h for h in self._m()["history"] if h["id"] == vid)
        return _hash_tree(self.root / vid) == e["sha"]
    def current(self): return self._m()["current"]
    def rollback(self, vid: str, target: str):
        if not self.verify(vid): raise RuntimeError("snapshot corrupted")
        t = Path(target)
        if t.exists(): shutil.rmtree(t)
        shutil.copytree(self.root / vid, t)
        m = self._m(); m["current"] = vid; self._save(m)
