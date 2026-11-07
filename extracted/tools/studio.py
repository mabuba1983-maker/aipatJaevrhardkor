# -*- coding: utf-8 -*-
"""Nuwaa Studio: everything needed to grow and develop the model on YOUR machine or server, with no dependence on anybody else.

  python tools/studio.py info                              what machine is this, what can it train
  python tools/studio.py consent grant FOLDER --days 30    give permission to read ONE folder (programming files and Arabic text only)
  python tools/studio.py consent list | revoke FOLDER|--all
  python tools/studio.py scan                              read ONLY the allowed folders -> studio/data/extra.txt + studio/scan_report.txt
  python tools/studio.py plan --size-gb 2                  numbers for a 2 GB model: parameters, memory, speed, and whether your data can feed it
  python tools/studio.py grow --size-gb 2                  build the bigger model (starts exactly like the current one)
  python tools/studio.py train --minutes 60 --cpu-percent 40    train in slices so the machine is never used more than you chose
  python tools/studio.py ladder --minutes-per-stage 120    GRADUAL growth 10M -> 40M -> 0.5 GB -> 1 GB -> 2 GB: each size is kept only if it beats the previous one
  python tools/studio.py serve --port 8000                 run the BIG model here; phones and browsers on your network talk to it
  python tools/studio.py export --fp16                     half-size weights file (a 2 GB model becomes 1 GB)
  python tools/studio.py loop --hours 8 --cpu-percent 40   scan -> train -> (self-play if you pressed the button) -> repeat
  python tools/studio.py press                             a human presses the button: allows ONE verified self-play round
  python tools/studio.py pack / verify PACK.zip            one zip with code + model + checksums, to move to another machine
Nothing here touches the network. Reads are limited to folders you allowed, expire, are logged, and never include secrets."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import prepare_corpus as pc
import scale_up

SKIP_DIRS = {"node_modules", "venv", "env", "__pycache__", "build", "dist", "target", "site-packages"}
SECRET_NAME = re.compile(r"(\.env|\.pem$|\.key$|\.p12$|\.pfx$|id_rsa|id_ed25519|credential|secret|passw|token|\.kdbx$|\.npmrc$|\.netrc$|\.htpasswd|keystore|\.jks$)", re.I)
SECRET_TEXT = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|(?i:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"\n]{6,})")
MAX_BYTES = 1_000_000

def default_home(): return ROOT / "studio"
def _j(path, default):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception: return default

# ---------------------------------------------------------------- consent
def grant(home, folder, days=30, now=None):
    now = time.time() if now is None else now; p = Path(folder).expanduser().resolve()
    if not p.is_dir(): raise ValueError(f"not a folder: {p}")
    if p == Path(p.anchor) or p == Path.home().resolve() or len(p.parts) <= 2:
        raise ValueError("too broad: allow a project folder, not a whole disk or your home folder")
    home = Path(home); home.mkdir(parents=True, exist_ok=True); c = _j(home / "consent.json", {"folders": []})
    c["folders"] = [f for f in c["folders"] if f["path"] != str(p)] + [{"path": str(p), "granted": now, "expires": now + days * 86400}]
    (home / "consent.json").write_text(json.dumps(c, indent=1), encoding="utf-8"); return p

def revoke(home, folder=None):
    c = _j(Path(home) / "consent.json", {"folders": []})
    c["folders"] = [] if folder is None else [f for f in c["folders"] if f["path"] != str(Path(folder).expanduser().resolve())]
    (Path(home) / "consent.json").write_text(json.dumps(c, indent=1), encoding="utf-8")

def active(home, now=None):
    now = time.time() if now is None else now
    return [Path(f["path"]) for f in _j(Path(home) / "consent.json", {"folders": []})["folders"] if f["expires"] > now]

def _inside(p, root):
    try: p.relative_to(root); return True
    except ValueError: return False

class Reader:
    """Reads files ONLY under allowed folders: programming files and Arabic text, no secrets, no symlink escapes, each read logged."""
    def __init__(self, home, now=None): self.home = Path(home); self.now = now; self.files = []; self.skipped = {}
    def _skip(self, why): self.skipped[why] = self.skipped.get(why, 0) + 1
    def docs(self):
        roots = active(self.home, self.now)
        if not roots: raise PermissionError("no folder is allowed (or the permission expired): run  studio.py consent grant FOLDER")
        self.home.mkdir(parents=True, exist_ok=True); log = open(self.home / "consent_log.jsonl", "a", encoding="utf-8")
        for root in roots:
            for dirpath, dirs, files in os.walk(root, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
                for f in sorted(files):
                    path = Path(dirpath) / f
                    if path.suffix.lower() not in pc.CODE_EXT | pc.TEXT_EXT: continue
                    if SECRET_NAME.search(f): self._skip("secret file name"); continue
                    try: real = path.resolve(strict=True)
                    except OSError: continue
                    if not _inside(real, root): self._skip("link leaving the allowed folder"); continue
                    if real.stat().st_size > MAX_BYTES: self._skip("too big"); continue
                    text = real.read_text(encoding="utf-8", errors="ignore")
                    if SECRET_TEXT.search(text): self._skip("looks like it holds a secret"); continue
                    self.files.append(str(real)); log.write(json.dumps({"t": time.time(), "read": str(real), "bytes": len(text)}) + "\n")
                    yield ("doc", text)
        log.close()

def scan(home, now=None):
    home = Path(home); r = Reader(home, now); (home / "data").mkdir(parents=True, exist_ok=True)
    st = pc.process(r.docs(), str(home / "data" / "extra.txt"))
    (home / "scan_report.txt").write_text("files read (%d):\n%s\nskipped: %s\nstatistics: %s\n" % (len(r.files), "\n".join(r.files), r.skipped, st), encoding="utf-8")
    st["files"] = len(r.files); st["skipped"] = r.skipped; return st

# ---------------------------------------------------------------- planning and growing
def plan(size_gb, data_chars):
    params = int(size_gb * 1e9 / 4); E = 128; H = scale_up.pick_hidden(params, E); n = scale_up.count(E, H)
    from nuwaa.lm import hw
    d = hw.info(); vram = max([g[1] for g in d["gpus"] if g[1] > 0] or [0.0])
    train_gb = n * 16 / 1e9 * 1.25        # weights + gradients + Adam (16 bytes per weight) plus room for activations
    out = {"emb": E, "hid": H, "params": n, "weights_gb": n * 4 / 1e9, "train_memory_gb": train_gb, "macs_per_char_million": 2 * (3 * H * (E + H) + 6 * H * H) / 1e6,
           "ram_gb": d["ram_gb"], "vram_gb": vram, "chars_per_weight": data_chars / n, "warnings": []}
    if vram and train_gb > vram: out["warnings"].append(f"the training state ({train_gb:.0f} GB) does not fit in the graphics card ({vram:.0f} GB)")
    if not vram and d["ram_gb"] and train_gb > d["ram_gb"]: out["warnings"].append(f"the training state ({train_gb:.0f} GB) does not fit in RAM ({d['ram_gb']:.0f} GB)")
    if not vram: out["warnings"].append("no graphics card found: training this size on the CPU would take months")
    if out["chars_per_weight"] < 1: out["warnings"].append(f"your data is {out['chars_per_weight']:.4f} characters per weight: the model will memorise it instead of understanding it. A model this size wants billions of characters of clean code and Arabic.")
    return out

def data_chars(home):
    n = 0
    for f in (Path(home) / "data" / "extra.txt",):
        if f.exists(): n += f.stat().st_size // 2
    from nuwaa.lm.corpus import all_pairs, fmt
    try: n += sum(len(fmt(*p)) for p in all_pairs(str(ROOT / "data")))
    except Exception: pass
    return n

def grow(home, size_gb, src=None, force=False):
    p = plan(size_gb, data_chars(home)); need_gb = p["weights_gb"] * 2.5
    if p["ram_gb"] and need_gb > p["ram_gb"] and not force: raise MemoryError(f"building needs about {need_gb:.0f} GB of RAM, this machine has {p['ram_gb']:.0f} GB (use --force to try anyway)")
    from nuwaa.lm.gru import GRULM
    old = GRULM.load(str(src or ROOT / "weights" / "nlm2.npz")); new = old.widened(p["emb"], p["hid"])
    out = Path(home) / "models" / f"nlm_{int(size_gb * 1000)}mb_init.npz"; out.parent.mkdir(parents=True, exist_ok=True); new.save(str(out)); return out, p

# ---------------------------------------------------------------- training in slices
def duty_sleep(work_s, pct): return 0.0 if pct >= 100 else work_s * (100 - pct) / pct

def train(home, minutes, cpu_percent, start=None, backend=None, chunk_steps=400):
    home = Path(home); models = home / "models"; models.mkdir(parents=True, exist_ok=True); cur = models / "current.npz"
    if not cur.exists(): shutil.copy(start or ROOT / "weights" / "nlm2.npz", cur)
    extra = home / "data" / "extra.txt"; end = time.time() + minutes * 60; slices = 0
    if backend is None:
        try:
            import torch; backend = "torch" if torch.cuda.is_available() else "numpy"
        except Exception: backend = "numpy"
    while time.time() < end:
        t0 = time.time()
        if backend == "torch":
            cmd = [sys.executable, str(ROOT / "tools" / "train_gru_torch.py"), "--init", str(cur), "--out", str(cur), "--steps", str(chunk_steps), "--bs", "64", "--amp"] + (["--text", str(extra)] if extra.exists() else [])
        else:
            cmd = [sys.executable, "-m", "nuwaa.lm.pretrain_gru", "--init", str(cur), "--out", str(cur), "--epochs", "1", "--seconds", "300", "--lr", "1e-3"] + (["--text", str(extra)] if extra.exists() else [])
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)          # a slice only overwrites `current.npz` when the held-out score IMPROVED
        with open(home / "log.jsonl", "a", encoding="utf-8") as f: f.write(json.dumps({"t": time.time(), "backend": backend, "seconds": round(time.time() - t0), "rc": r.returncode, "tail": r.stdout[-300:]}, ensure_ascii=False) + "\n")
        slices += 1; time.sleep(duty_sleep(time.time() - t0, cpu_percent))
    return slices

LADDER = [("10M", 10_000_000), ("40M", 40_000_000), ("125M = 0.5 GB", 125_000_000), ("250M = 1 GB", 250_000_000), ("500M = 2 GB", 500_000_000)]

def heldout_bits(path, home):
    """Bits per character of a model on a FIXED held-out text (every 53rd pair of the built-in data, and every 97th line of the allowed-folders text)."""
    from nuwaa.lm.gru import GRULM
    from nuwaa.lm.corpus import all_pairs, fmt
    pairs = all_pairs(str(ROOT / "data")); text = "\n" + "".join(fmt(*p) for i, p in enumerate(pairs) if i % 53 == 7)
    ex = Path(home) / "data" / "extra.txt"
    if ex.exists(): text += "".join(l.rstrip("\n").replace("\tج:", "\nج:", 1) + "\n" for i, l in enumerate(open(ex, encoding="utf-8")) if i % 97 == 3)
    m = GRULM.load(str(path)); return m.bpc(m.encode(text[:6000], grow=False))

def ladder(home, minutes_per_stage=120, min_gain=0.02, cpu_percent=100, dry=False, grow_fn=None, train_fn=None, score_fn=None, params_fn=None, log=print):
    """GRADUAL growth: a bigger model is only kept if it BEATS the smaller one on the held-out text after training. Otherwise the smaller one is restored and the
    ladder stops with the reason (usually: the data is too small for this size). Resumable: it always continues from studio/models/current.npz."""
    from nuwaa.lm.gru import GRULM
    home = Path(home); cur = home / "models" / "current.npz"; (home / "models").mkdir(parents=True, exist_ok=True)
    grow_fn = grow_fn or (lambda src, size_gb, dst: _grow_to(src, size_gb, dst)); train_fn = train_fn or (lambda: train(home, minutes_per_stage, cpu_percent))
    score_fn = score_fn or (lambda p: heldout_bits(p, home))
    if not cur.exists(): shutil.copy(ROOT / "weights" / "nlm2.npz", cur)
    state = _j(home / "ladder.json", {"history": []}); done = []
    for name, target in LADDER:
        n_now = (params_fn or (lambda q: GRULM.load(str(q)).n_params()))(cur) if not dry else 0
        if not dry and n_now >= target * 0.98: continue
        p = plan(target * 4 / 1e9, data_chars(home))
        if dry: log(f"stage {name}: {p['params']:,} weights, training memory {p['train_memory_gb']:.1f} GB, data/weight {p['chars_per_weight']:.4f}, warnings: {p['warnings'] or 'none'}"); continue
        if any("does not fit" in w for w in p["warnings"]): log(f"STOP before {name}: " + "; ".join(w for w in p["warnings"] if "does not fit" in w)); break
        before = score_fn(cur); backup = home / "models" / "before_growth.npz"; shutil.copy(cur, backup)
        grow_fn(cur, target * 4 / 1e9, cur); train_fn(); after = score_fn(cur)
        gain = (before - after) / before; state["history"].append({"stage": name, "before": before, "after": after, "gain": gain, "t": time.time()}); (home / "ladder.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
        if gain < min_gain:
            shutil.copy(backup, cur); log(f"HALT at {name}: it improved only {gain * 100:.1f}% (needed {min_gain * 100:.0f}%). The smaller model was restored. Add more data before growing."); break
        log(f"kept {name}: held-out {before:.3f} -> {after:.3f} bits/char ({gain * 100:.1f}% better)"); done.append(name)
    return done

def _grow_to(src, size_gb, dst):
    from nuwaa.lm.gru import GRULM
    p = plan(size_gb, 1); old = GRULM.load(str(src)); new = old.widened(p["emb"], p["hid"]); new.save(str(dst))

def export_fp16(home, out=None):
    from nuwaa.lm.gru import GRULM
    cur = Path(home) / "models" / "current.npz"; out = Path(out or Path(home) / "models" / "current_fp16.npz"); GRULM.load(str(cur)).save(str(out), fp16=True); return out

def serve(home, port=8000, weights=None):
    """Runs the chat server (server/server.py) with the BIG model on this machine: phones and browsers on the same network talk to it, so the model can be
    far bigger than a phone could hold. The weights are NUWAA_WEIGHTS (default: studio/models/current.npz)."""
    os.environ["NUWAA_WEIGHTS"] = str(weights or Path(home) / "models" / "current.npz")
    sys.path.insert(0, str(ROOT / "server")); import server as srv
    app = srv.App(); print("Nuwaa server with", os.environ["NUWAA_WEIGHTS"], f"-> http://0.0.0.0:{port}"); srv.make_server(app, "0.0.0.0", port).serve_forever()

def press(home):
    from nuwaa.selfimprove.button import record_press
    record_press(str(Path(home) / "press.json"), "human-at-the-keyboard"); return Path(home) / "press.json"

def loop(home, hours, cpu_percent, selfplay=False):
    end = time.time() + hours * 3600; rounds = 0
    while time.time() < end:
        try: scan(home)
        except PermissionError: pass                    # no allowed folder: train on the built-in data only
        train(home, min(30, max(1, (end - time.time()) / 60)), cpu_percent)
        if selfplay and (Path(home) / "press.json").exists():
            subprocess.run([sys.executable, "-m", "nuwaa.lm.selfplay", "--weights", str(Path(home) / "models" / "current.npz"), "--out", str(Path(home) / "models" / "current_selfplay.npz"), "--press", str(Path(home) / "press.json")], cwd=str(ROOT))
        rounds += 1
    return rounds

# ---------------------------------------------------------------- one zip to move anywhere
def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def pack(home, out, private=False, root=ROOT):
    home = Path(home); root = Path(root); files = []
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in {".git", "__pycache__", "studio", "node_modules", ".gradle", "build"}]
        files += [Path(r) / f for f in fs if not f.endswith(".pyc") and f != Path(out).name]
    for f in (home / "models").glob("*.npz") if (home / "models").exists() else []: files.append(f)
    if private:
        for n in ("consent.json", "consent_log.jsonl", "scan_report.txt", "log.jsonl"):
            if (home / n).exists(): files.append(home / n)
        if (home / "data" / "extra.txt").exists(): files.append(home / "data" / "extra.txt")
    man = {"made": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {}}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            name = ("studio/" + f.relative_to(home).as_posix()) if _inside(f, home) else f.relative_to(root).as_posix()
            man["files"][name] = _sha(f); z.write(f, name)
        z.writestr("MANIFEST.json", json.dumps(man, indent=1))
    return len(files)

def verify(pack_path):
    bad = []
    with zipfile.ZipFile(pack_path) as z:
        man = json.loads(z.read("MANIFEST.json"))
        for name, sha in man["files"].items():
            if hashlib.sha256(z.read(name)).hexdigest() != sha: bad.append(name)
    return bad

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--home", default=str(default_home())); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info"); c = sub.add_parser("consent"); c.add_argument("what", choices=["grant", "list", "revoke"]); c.add_argument("folder", nargs="?"); c.add_argument("--days", type=int, default=30); c.add_argument("--all", action="store_true")
    sub.add_parser("scan"); p = sub.add_parser("plan"); p.add_argument("--size-gb", type=float, default=2.0); g = sub.add_parser("grow"); g.add_argument("--size-gb", type=float, default=2.0); g.add_argument("--force", action="store_true")
    t = sub.add_parser("train"); t.add_argument("--minutes", type=float, default=60); t.add_argument("--cpu-percent", type=int, default=40)
    l = sub.add_parser("loop"); l.add_argument("--hours", type=float, default=8); l.add_argument("--cpu-percent", type=int, default=40); l.add_argument("--selfplay", action="store_true")
    ad = sub.add_parser("autodev"); ad.add_argument("--rounds", type=int, default=6); ad.add_argument("--minutes-per-round", type=float, default=10)
    ad.add_argument("--lr", type=float, default=4e-4); ad.add_argument("--tolerance", type=float, default=0.08)
    sub.add_parser("press"); lad = sub.add_parser("ladder"); lad.add_argument("--minutes-per-stage", type=float, default=120); lad.add_argument("--min-gain", type=float, default=0.02); lad.add_argument("--cpu-percent", type=int, default=100); lad.add_argument("--dry", action="store_true")
    ex = sub.add_parser("export"); ex.add_argument("--fp16", action="store_true"); sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8000); sv.add_argument("--weights", default=""); k = sub.add_parser("pack"); k.add_argument("--out", default="NuwaaStudio.zip"); k.add_argument("--with-private", action="store_true"); v = sub.add_parser("verify"); v.add_argument("pack")
    a = ap.parse_args(argv); home = Path(a.home)
    if a.cmd == "info":
        from nuwaa.lm import hw; print(hw.report())
    elif a.cmd == "consent":
        if a.what == "grant": print("allowed:", grant(home, a.folder, a.days), f"for {a.days} days. Only programming files and Arabic text are read; secrets are skipped; every read is logged in {home / 'consent_log.jsonl'}")
        elif a.what == "revoke": revoke(home, None if a.all else a.folder); print("revoked")
        else: print("\n".join(f"{p}" for p in active(home)) or "no allowed folders")
    elif a.cmd == "scan": print(json.dumps(scan(home), ensure_ascii=False, indent=1)); print("report:", home / "scan_report.txt")
    elif a.cmd == "plan": print(json.dumps(plan(a.size_gb, data_chars(home)), ensure_ascii=False, indent=1))
    elif a.cmd == "grow": out, p = grow(home, a.size_gb, force=a.force); print("built", out, f"({p['params']:,} weights)"); [print("WARNING:", w) for w in p["warnings"]]
    elif a.cmd == "train": print("slices:", train(home, a.minutes, a.cpu_percent))
    elif a.cmd == "loop": print("rounds:", loop(home, a.hours, a.cpu_percent, a.selfplay))
    elif a.cmd == "autodev":
        sys.path.insert(0, str(ROOT))
        from nuwaa.lm import autodev
        cur = Path(home) / "models" / "current.npz"; (Path(home) / "models").mkdir(parents=True, exist_ok=True)
        if not cur.exists(): shutil.copy(ROOT / "weights" / "nlm2.npz", cur)
        extra = Path(home) / "data" / "extra.txt"
        n, hist = autodev.run(str(cur), str(cur), a.rounds, a.minutes_per_round, a.lr, a.tolerance, str(extra) if extra.exists() else None)
        print(f"accepted {n}/{a.rounds} rounds (every round measured on 4 independent skills: pairs/files/review/arabic, not just one average)")
    elif a.cmd == "ladder": print("stages kept:", ladder(home, a.minutes_per_stage, a.min_gain, a.cpu_percent, a.dry))
    elif a.cmd == "export": print("written:", export_fp16(home))
    elif a.cmd == "serve": serve(home, a.port, a.weights or None)
    elif a.cmd == "press": print("press recorded:", press(home), "(valid for one hour, one self-play round)")
    elif a.cmd == "pack": print("files:", pack(home, a.out, a.with_private), "->", a.out)
    elif a.cmd == "verify": bad = verify(a.pack); print("all files match their checksums" if not bad else "CORRUPTED: " + ", ".join(bad)); sys.exit(1 if bad else 0)

if __name__ == "__main__": main()
